# encoding: utf-8
import os
import argparse

from workflow import web, Workflow, PasswordNotFound

from gitlab import get_all_pages
from accounts import ManageGitlabAccounts


def main(wf):
    logger = wf.logger

    try:
        all_accounts = ManageGitlabAccounts._load_all_accounts()
        acc_to_update = all_accounts.copy()

        cache_path = wf.cachefile('%s.%s' % ('all_projects', wf.cache_serializer))
        logger.info('Removing cache: {}'.format(cache_path))
        try:
            os.remove(cache_path)
        except:
            pass

        def wrapper():
            """`cached_data` can only take a bare callable (no args),
            so we need to wrap callables needing arguments in a function
            that needs none.
            """

            result = []
            for url, api_key in acc_to_update.values():
                logger.info('base api url is: {url}; api token is: {token}'.format(url=url, token=api_key))
                result.extend(get_all_pages(api_token=api_key, base_url=url))
                logger.info(result)
            return result

        all_projects = wf.cached_data('all_projects', wrapper)

        print('{} Gitlab repos cached'.format(len(all_projects)))
        wf.logger.debug('{} Gitlab repos cached'.format(len(all_projects)))

    except PasswordNotFound:  # API key has not yet been set
        wf.logger.error('No API key saved')
        print('No API key saved')


if __name__ == u"__main__":
    print('start')

    wf = Workflow()
    sys.exit(wf.run(main))
