#!/usr/bin/python
# encoding: utf-8

"""
Main search script for alfred-bear workflow.
"""

import sys
import argparse
import queries
import io
import ccl_bplist
import time
from workflow import Workflow, ICON_SYNC


TITLE = "i"
PROJECT = "p"

SINGLE_QUOTE = "'"
ESC_SINGLE_QUOTE = "''"

LOGGER = None

APPLE_COCOA_TIME_OFFSET = 978307200

ccl_bplist.set_object_converter(ccl_bplist.NSKeyedArchiver_common_objects_convertor)

# Update workflow from GitHub repo
UPDATE_SETTINGS = {'github_slug': 'tinng81/alfred-agenda'}
SHOW_UPDATES = True


def main(workflow):
    """
    I'm just here so I don't get fined by pylint
    """

    if SHOW_UPDATES and workflow.update_available:
        workflow.add_item('A new version is available',
                          'Action this item to install the update',
                          autocomplete='workflow:update',
                          icon=ICON_SYNC)

    LOGGER.debug('Started search workflow')
    args = parse_args()

    if args.query:
        query = args.query[0]
        LOGGER.debug("Searching notes for %s", format(query))
        execute_search_query(args)

    workflow.send_feedback()


def parse_args():
    """
    Parses out the arguments sent to the script in the Alfred workflow.
    """

    parser = argparse.ArgumentParser(description="Search Agenda Notes")
    parser.add_argument('-t', '--type', default=TITLE,
                        choices=[TITLE, PROJECT],
                        type=str, help='What to search for: t(i)tle, or (p)roject?')
    parser.add_argument('-p', '--project_only', default=False,
                        type=bool, help='Search project only?')
    parser.add_argument('query', type=unicode,
                        nargs=argparse.REMAINDER, help='query string')

    LOGGER.debug(WORKFLOW.args)
    args = parser.parse_args(WORKFLOW.args)
    return args

def is_deleted(title_result):
    """
    Takes a single note query result, deserialises the note properties, and returns if the note is deleted.
    """
    properties_blob = io.BytesIO(title_result[2])
    properties_plist = ccl_bplist.load(properties_blob)
    properties = ccl_bplist.deserialise_NsKeyedArchiver(properties_plist)
    return properties.get('markedDeleted')

def execute_search_query(args):
    """
    Decides what search to run based on args that were passed in and executes the search.
    """
    query = None
    if args.query:
        query = args.query[0]
        query = query.encode('utf-8')

        if SINGLE_QUOTE in query:
            query = query.replace(SINGLE_QUOTE, ESC_SINGLE_QUOTE)

    if args.type == PROJECT:
        LOGGER.debug('Searching projects')
        project_results = queries.search_projects_by_title(WORKFLOW, LOGGER, query)
        if not args.project_only:
            note_results = queries.search_notes_by_project_title(WORKFLOW, LOGGER, query)
        if not project_results:
            WORKFLOW.add_item('No search results found.')
        else:
            for project_result in project_results:
                # LOGGER.debug(project_result)
                project_arg = ':p:' + project_result[0]
                WORKFLOW.add_item(title=project_result[1], 
                                  subtitle=("Open this project from \"" + project_result[2] + "\" Category") 
                                    if not args.project_only else "Add this note to project \"" + project_result[1] + "\"",
                                  arg=project_arg, valid=True)
            
            # NOTE added logic to exclude note search by project title
            if not args.project_only:
                for note_result in note_results:
                    if not is_deleted(note_result):
                        # LOGGER.debug(note_results)
                        note_arg = ':n:' + note_result[0]

                        if note_result[3] is None:
                            subtitle = " "
                        else:
                            note_date = time.localtime(note_result[3] + APPLE_COCOA_TIME_OFFSET)
                            LOGGER.debug(note_date)
                            if note_date.tm_hour == 0 and note_date.tm_min == 0:
                                subtitle = time.strftime('Last edit: %d %b %Y', note_date)
                            else:
                                subtitle = time.strftime('Last edit: %d %b %Y %H:%M', note_date)
                        WORKFLOW.add_item(title=note_result[1], subtitle=subtitle + " from \"" + note_result[4] + "\" Project",
                                        arg=note_arg, valid=True)

    else:
        LOGGER.debug('Searching notes')
        title_results = queries.search_notes_by_title(WORKFLOW, LOGGER, query)
        if not title_results:
            WORKFLOW.add_item('No search results found.')
        else:
            note_ids = []
            for title_result in title_results:
                if not is_deleted(title_result):
                    LOGGER.debug(title_result)
                    if title_result[3] is None:
                        subtitle = "Open note"
                    else:
                        note_date = time.localtime(title_result[3] + APPLE_COCOA_TIME_OFFSET)
                        if note_date.tm_hour == 0 and note_date.tm_min == 0:
                            subtitle = time.strftime('Last edit: %d %b %Y', note_date)
                        else:
                            subtitle = time.strftime('Last edit: %d %b %Y %H:%M', note_date)                 
                    WORKFLOW.add_item(title=title_result[1], subtitle=subtitle + " from \"" + title_result[4] + "\" Project", 
                                      arg=title_result[0], valid=True)
                    note_ids.append(title_result[0])


if __name__ == '__main__':
    WORKFLOW = Workflow(update_settings=UPDATE_SETTINGS)
    LOGGER = WORKFLOW.logger
    sys.exit(WORKFLOW.run(main))
