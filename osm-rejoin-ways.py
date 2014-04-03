import argparse
import psycopg2
import sys

def parse_args(argv):
    parser = argparse.ArgumentParser(description='')
    # Postgres connection details
    parser.add_argument("-u", "--username")
    parser.add_argument("-H", "--hostname")
    parser.add_argument("-d", "--database", default="gis")
    parser.add_argument("-p", "--password")

    # where you data is
    parser.add_argument("--prefix", default="planet_osm")
    parser.add_argument("-t", "--tags", default="ref,name")
    parser.add_argument("-w", "--where")

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
    db_connection.commit()

def populate_start_end_columns(db_connection, table_name):
    cursor = db_connection.cursor()
    # Only update rows we need to, i.e. where start_x has not been set.
    # We presume if start_x is non-null then all the other columns are non-null
    # too.
    cursor.execute("UPDATE {table_name} SET start_x = ST_X(ST_StartPoint(way)), start_y = ST_Y(ST_StartPoint(way)), end_x = ST_X(ST_EndPoint(way)), end_y = ST_Y(ST_EndPoint(way)) WHERE start_x IS NULL".format(table_name=table_name))
    db_connection.commit()


def join_up_based_on_tag_value(db_connection, table_name, tag, value, where_clause):
    print "Merging {0}={1}".format(tag, value)
    with db_connection.cursor() as cursor:
        while True:
            cursor.execute("select a.osm_id, b.osm_id from (select osm_id, {tag}, start_x, start_y, end_x, end_y from {table_name} WHERE {where_clause}) as a join (select osm_id, {tag}, start_x, start_y, end_x, end_y FROM planet_osm_line WHERE {where_clause}) as b ON ( (a.osm_id < b.osm_id) AND (a.{tag} = '{value}' and b.{tag} = '{value}') and ((a.start_x = b.end_x and a.start_y = b.end_y) OR (a.start_x = b.start_x and a.start_y = b.start_y)));".format(table_name=table_name, tag=tag, value=value, where_clause=where_clause))
            connections = list(cursor)

            if len(connections) == 0:
                # Nothing to do here
                break

            print "There are {} connections".format(len(connections))

            for a_osm_id, b_osm_id in connections:
                # ensure both are still there are can be joined (in case one
                # part was joined to another part earlier
                cursor.execute("SELECT osm_id, start_x, start_y, end_x, end_y from {table_name} where osm_id IN (%s, %s)".format(table_name=table_name), (a_osm_id, b_osm_id))
                osm_ids = list(cursor)
                if len(osm_ids) == 0:
                    # neither left, both delted?
                    pass
                elif len(osm_ids) == 1:
                    # one deleted?
                    pass
                elif len(osm_ids) == 2:
                    # delete #1 and update #2 geom
                    #cursor.execute("""
                    #    WITH output AS ( DELETE FROM {table_name} where osm_id = {osm_id_0} returning way )
                    #        UPDATE {table_name} SET way = ST_MakeLine(way, output.way) WHERE osm_id = {osm_id_1} FROM output
                    #""".format(table_name=table_name, osm_id_0=osm_ids[0][0], osm_id_1=osm_ids[1][0]))
                    cursor.execute("""
                        UPDATE {table_name} SET way = ( SELECT ST_MakeLine(way) from {table_name} WHERE osm_id IN (%s, %s) ) WHERE osm_id = %s
                    """.format(table_name=table_name), (osm_ids[0][0], osm_ids[1][0], osm_ids[1][0]))
                    # Update end point of #2
                    cursor.execute("UPDATE {table_name} SET start_x = ST_X(ST_StartPoint(way)), start_y = ST_Y(ST_StartPoint(way)), end_x = ST_X(ST_EndPoint(way)), end_y = ST_Y(ST_EndPoint(way)) WHERE osm_id = %s".format(table_name=table_name), (osm_ids[1][0],))
                    cursor.execute("DELETE FROM {table_name} where osm_id = %s".format(table_name=table_name), (osm_ids[0][0],))
                    print "Merged osm_ids {osm_id_0} into {osm_id_1}".format(osm_id_0=osm_ids[0][0], osm_id_1=osm_ids[1][0])

                else:
                    # WTF?
                    import pdb; pdb.set_trace()
                    raise NotImplementedError("Impossible Code path ")

            break

                #cursor.execute("UPDATE planet_osm_line SET select a.osm_id, b.osm_id from {table_name} as a join planet_osm_line as b ON ( (a.osm_id < b.osm_id) AND (a.{tag} = '{value}' and b.{tag} = '{value}') and ((a.start_x = b.end_x and a.start_y = b.end_y) OR (a.start_x = b.start_x and a.start_y = b.start_y)));")



    #select a.osm_id, b.osm_id from planet_osm_line as a join planet_osm_line as b ON ( (a.osm_id < b.osm_id) AND (a.ref = 'N59' and b.ref = 'N59') and ((a.start_x = b.end_x and a.start_y = b.end_y) OR (a.start_x = b.start_x and a.start_y = b.start_y)));

def join_up_based_on_tag(db_connection, table_name, tag, where_clause):
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT {tag} from {table_name} WHERE {tag} IS NOT NULL AND {where_clause}".format(tag=tag, table_name=table_name, where_clause=where_clause))
        distinct_tag_values = set(x[0] for x in cursor)

    for tag_value in distinct_tag_values:
        join_up_based_on_tag_value(db_connection, table_name, tag, tag_value, where_clause)



def main(argv):
    args = parse_args(argv)
    db_connection = connect_to_database(args)
    table_name = args.prefix + "_line"
    add_start_end_columns(db_connection, table_name)
    populate_start_end_columns(db_connection, table_name)

    where_clause = args.where or '1 = 1'

    for tag in args.tags.split(","):
        tag = tag.strip()
        join_up_based_on_tag(db_connection, table_name, tag, where_clause)



if __name__ == '__main__':
    main(sys.argv[1:])
