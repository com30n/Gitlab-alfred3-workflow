# -*- coding: utf-8 -*-
import sys
import ujson as json
import requests

from urlparse import urljoin, urlparse

from workflow import Workflow3 as Workflow, ICON_WEB, ICON_WARNING, ICON_INFO, PasswordNotFound

from accounts import ManageGitlabAccounts

wf = Workflow()
logger = wf.logger

CMD_SEARCH = {'title': 'Find project in your GitLab', 'arg': 'gitlabSearch', 'valid': 'True'}
CMD_UPDATE = {'title': 'Update cache', 'arg': 'updateRepoCache', 'valid': 'True'}
CMD_ACCOUNT_LIST = {'title': 'Show accounts list', 'arg': 'listAccounts', 'valid': 'True'}
CMD_ADD_ACCOUNT = {'title': 'Add new gitlab account', 'subtitle': 'Add account to keychain', 'arg': 'addAccount',
                   'valid': 'True'}
CMD_DEL_ACCOUNT = {'title': 'Del gitlab account', 'subtitle': 'Remove account from keychain', 'arg': 'delAccount',
                   'valid': 'True'}

manage_cmd = [
    CMD_SEARCH,
    CMD_UPDATE,
    CMD_ACCOUNT_LIST,
    CMD_ADD_ACCOUNT,
    CMD_DEL_ACCOUNT
]


def get_all_pages(api_token, base_url):
    result = []
    gitlab_api_base = urljoin(base_url, 'api/v4/')
    gitlab_api_per_page = 'per_page=100'

    gitlab_api_projects_url = '{gitlab_api}?private_token={gitlab_token}&{per_page}'.format(
        gitlab_api=urljoin(gitlab_api_base, 'projects'),
        gitlab_token=api_token,
        per_page=gitlab_api_per_page
    )
    logger.debug('Try to get {}'.format(gitlab_api_projects_url))
    response = requests.get('{api_url}&page={page}'.format(api_url=gitlab_api_projects_url, page=0), verify=False)
    response.raise_for_status()
    result.extend(response.json())

    while response.headers['X-Next-Page'] != '':
        logger.debug('Try to get {}'.format(
            '{api_url}&page={page}'.format(api_url=gitlab_api_projects_url, page=response.headers['X-Next-Page'])))
        response = requests.get(
            '{api_url}&page={page}'.format(api_url=gitlab_api_projects_url, page=response.headers['X-Next-Page']),
            verify=False)
        response.raise_for_status()
        result.extend(response.json())

    return result


def search_key_for_projects(projects):
    """Generate a string search key for a projects"""
    elements = [
        projects['name_with_namespace'],
        projects['path_with_namespace'],
        projects['web_url']
    ]
    return u' '.join(elements)


def check_gitlab_url(url):
    parsed_url = urlparse(url)
    if not parsed_url.netloc:
        raise requests.HTTPError('Please, verify the presence of the net scheme (http:// or https://)')

    response = requests.get('https://{url}/'.format(url=parsed_url.netloc), verify=False)
    response.raise_for_status()


def search(query):
    ####################################################################
    # Check that we have an API key saved
    ####################################################################

    try:
        # api_key = wf.get_password('gitlab_api_key')
        all_gitlab_accounts = ManageGitlabAccounts._load_all_accounts()
        logger.info(all_gitlab_accounts)

    except PasswordNotFound:  # API key has not yet been set
        wf.add_item('No API key set.',
                    'Please use glsetkey to set your GitLab API key and set Gitlab base API URL.',
                    valid=False,
                    icon=ICON_WARNING)
        wf.send_feedback()
        return 0

    ####################################################################
    # View/filter GitLab repos
    ####################################################################

    # Retrieve posts from cache if available and no more than 600
    # seconds old

    def wrapper():
        """`cached_data` can only take a bare callable (no args),
        so we need to wrap callables needing arguments in a function
        that needs none.
        """
        result = []
        for url, api_key in all_gitlab_accounts.values():
            logger.info('base api url is: {url}; api token is: {token}'.format(url=url, token=api_key))
            result.extend(get_all_pages(api_token=api_key, base_url=url))
        return result

    # all_projects = get_from_cache()
    all_projects = wf.cached_data('all_projects', wrapper, max_age=0)

    # If script was passed a query, use it to filter posts
    all_projects = wf.filter(query, all_projects, key=search_key_for_projects, min_score=20)

    if not all_projects:
        wf.add_item('No repos found', icon=ICON_WARNING)
        wf.send_feedback()
        return 0

    for service_name in all_projects:
        wf.add_item(
            title=service_name['name_with_namespace'],
            subtitle=service_name['web_url'],
            arg=json.dumps(service_name),
            valid=True,
            icon=ICON_WEB,
        )

    wf.send_feedback()


def manager(wf):
    for item in manage_cmd:
        wf.add_item(**item)

    wf.send_feedback()


if __name__ == u'__main__':
    sys.exit(wf.run(manager))
