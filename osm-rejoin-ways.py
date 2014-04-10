import argparse
import psycopg2
import sys

def parse_args(argv):
    parser = argparse.ArgumentParser(description='')
    # Postgres connection details
    # TODO support all connection options
    #parser.add_argument("-u", "--username")
    #parser.add_argument("-H", "--hostname")
    #parser.add_argument("-p", "--password")
    parser.add_argument("-d", "--database", default="gis", help="PostgreSQL database")

    # where you data is
    parser.add_argument("--prefix", default="planet_osm", help="Table prefix")
    parser.add_argument("-t", "--tags", default="ref,name,highway", help="tags to merge ways on")

    parser.add_argument("-w", "--where" default="highway IS NOT NULL", help="Only rows that match this SQL WHERE query are worked on")

    args = parser.parse_args(argv)

    return args


def connect_to_database(args):
    # TODO support usernames etc
    return psycopg2.connect("dbname=" + args.database)


def add_start_end_columns(db_connection, table_name):
    cursor = db_connection.cursor()
    cursor.execute("SELECT 1 FROM information_schema.columns WHERE table_name=%s and column_name=%s LIMIT 1", (table_name, 'start_x'))
    if len(list(cursor)) != 0:
        return

    for column in ['start_x', 'start_y', 'end_x', 'end_y']:
        # add column
        cursor.execute("ALTER TABLE {table_name} ADD COLUMN {column} float".format(table_name=table_name, column=column))

    cursor.execute("CREATE INDEX {table_name}__start_point ON {table_name} (start_x, start_y)".format(table_name=table_name))
    cursor.execute("CREATE INDEX {table_name}__end_point ON {table_name} (end_x, end_y)".format(table_name=table_name))

    # Create index on fields we're searching on?
    db_connection.commit()

def populate_start_end_columns(db_connection, table_name):
    cursor = db_connection.cursor()
    # Only update rows we need to, i.e. where start_x has not been set.
    # We presume if start_x is non-null then all the other columns are non-null
    # too.
    cursor.execute("UPDATE {table_name} SET start_x = ST_X(ST_StartPoint(way)), start_y = ST_Y(ST_StartPoint(way)), end_x = ST_X(ST_EndPoint(way)), end_y = ST_Y(ST_EndPoint(way)) WHERE start_x IS NULL".format(table_name=table_name))
    db_connection.commit()


def create_index_on_tags(db_connection, table_name, tags):
    with db_connection.cursor() as cursor:
        for tag in tags:
            cursor.execute("CREATE INDEX ON {table_name} ({tag});".format(table_name=table_name, tag=tag))

def join_up_based_on_tag_value(db_connection, table_name, tag, value, where_clause, null_clause):
    num_iterations = 0
    max_iterations = 100

    while True:
        if num_iterations > max_iterations:
            break
        num_iterations += 1
        with db_connection.cursor() as cursor:

            cursor.execute("select a.osm_id, b.osm_id from (select osm_id, {tag}, way from {table_name} WHERE {where_clause} {null_clause}) as a join (select osm_id, {tag}, way FROM {table_name} WHERE {where_clause} {null_clause}) as b ON ( (a.osm_id <> b.osm_id) AND (a.{tag} = %s and b.{tag} = %s) and st_intersects(a.way, b.way));".format(table_name=table_name, tag=tag, where_clause=where_clause, null_clause=null_clause), (value, value))
            connections = list(cursor)

            if len(connections) == 0:
                # Nothing to do here
                break

            print "Merging {0}={1}, there are {2} connections, iteration = {3}".format(tag, value, len(connections)+1, num_iterations)

            for a_osm_id, b_osm_id in connections:
                # ensure both are still there are can be joined (in case one
                # part was joined to another part earlier
                cursor.execute("SELECT osm_id from {table_name} where osm_id IN (%s, %s)".format(table_name=table_name), (a_osm_id, b_osm_id))
                osm_ids = list(cursor)
                if len(osm_ids) == 0 or len(osm_ids) == 1:
                    # both deleted or one deleted
                    pass
                elif len(osm_ids) == 2:
                    # update #2 geom
                    cursor.execute("""
                        UPDATE {table_name} SET way = ( SELECT ST_Union(way) from {table_name} WHERE osm_id IN (%s, %s) ) WHERE osm_id = %s
                    """.format(table_name=table_name), (osm_ids[0][0], osm_ids[1][0], osm_ids[1][0]))
                    # Update end point of #2
                    #cursor.execute("UPDATE {table_name} SET start_x = ST_X(ST_StartPoint(way)), start_y = ST_Y(ST_StartPoint(way)), end_x = ST_X(ST_EndPoint(way)), end_y = ST_Y(ST_EndPoint(way)) WHERE osm_id = %s".format(table_name=table_name), (osm_ids[1][0],))
                    # delete #1
                    cursor.execute("DELETE FROM {table_name} where osm_id = %s".format(table_name=table_name), (osm_ids[0][0],))
                    print "\tMerged osm_ids {osm_id_0} into {osm_id_1}".format(osm_id_0=osm_ids[0][0], osm_id_1=osm_ids[1][0])

                else:
                    # WTF?
                    raise NotImplementedError("Impossible Code path ")

            db_connection.commit()


def join_up_based_on_tag(db_connection, table_name, tag, where_clause, null_columns):
    null_columns = null_columns or []
    # TODO merge this into where_clause
    if len(null_columns) == 0:
        null_clause = ''
    else:
        null_clause = ' AND ' + " AND ".join(x+" IS NULL" for x in null_columns)

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT {tag} from {table_name} WHERE {tag} IS NOT NULL AND {where_clause}".format(tag=tag, table_name=table_name, where_clause=where_clause))
        distinct_tag_values = set(x[0] for x in cursor)

    for tag_value in distinct_tag_values:
        join_up_based_on_tag_value(db_connection, table_name, tag, tag_value, where_clause, null_clause)



def main(argv):
    args = parse_args(argv)
    tags = [t.strip() for t in args.tags.split(",")]
    db_connection = connect_to_database(args)
    table_name = args.prefix + "_line"
    add_start_end_columns(db_connection, table_name)
    populate_start_end_columns(db_connection, table_name)
    create_index_on_tags(db_connection, table_name, tags)

    where_clause = args.where or '1 = 1'

    already_examined_tags = []
    for tag in tags:
        join_up_based_on_tag(db_connection, table_name, tag, where_clause, null_columns=already_examined_tags)
        already_examined_tags.append(tag)



if __name__ == '__main__':
    main(sys.argv[1:])
