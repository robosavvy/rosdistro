#!/usr/bin/env python3

# Copyright (c) 2017, Open Source Robotics Foundation
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Willow Garage, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import argparse
import os
import sys
from github import Github, UnknownObjectException


def detect_repo_hook(repo, cb_url):
    for hook in repo.get_hooks():
        config = hook.config
        if 'url' in config and config['url'] == cb_url:
            return True
    return False


class GHPRBHookDetector(object):
    def __init__(self, github_user, github_token, callback_url):
        self.callback_url = callback_url
        self.gh = Github(github_user, github_token)

    def get_repo(self, username, reponame):
        try:
            repo = self.gh.get_user(username).get_repo(reponame)
        except UnknownObjectException as ex:
            # print(ex)
            print('Failed to access repo [ %s/%s ]' % (username, reponame))
            return None
        return repo

    def check_repo_for_access(self, repo, errors, strict=False):
        push_access = repo.permissions.push
        admin_access = repo.permissions.admin
        try:
            hook_detected = detect_repo_hook(repo, self.callback_url)
        except UnknownObjectException as ex:
            errors.append('Unable to check repo [ %s ] for hooks' % repo.full_name)
            hook_detected = False
        if push_access and hook_detected or admin_access:
            return True
        if push_access and not hook_detected:
            print('Warning: Push access detected but unable to verify manual hook '
                'configuration for repo [ %s ]. Please visit ' % repo.full_name +
                'http://wiki.ros.org/buildfarm/Pull%20request%20testing '
                'and make sure hooks are setup.')
            if strict:
                return False
            else:
                errors.append('Warning: Push access detected but unable to verify manual hook '
                    'configuration for repo [ %s ]. Please visit ' % repo.full_name +
                    'http://wiki.ros.org/buildfarm/Pull%20request%20testing '
                    'and make sure hooks are setup.')
                return True

def check_hooks_on_repo(user, repo, errors, hook_user='ros-pull-request-builder', callback_url='http://build.ros.org/ghprbhook/', token=None, strict=False):

    ghprb_detector = GHPRBHookDetector(hook_user, token, callback_url)

    test_repo = ghprb_detector.get_repo(user, repo)

    if test_repo:
        hooks_ok = ghprb_detector.check_repo_for_access(test_repo, errors, strict=strict)
        if hooks_ok:
            print('Passed ghprb_detector check for hooks access'
                  ' for repo [ %s ]' % test_repo.full_name)
            return True
        else:
            print('ERROR: Not enough permissions to setup pull request'
                  ' builds for repo [ %s ] ' % (test_repo.full_name) +
                  'Please see http://wiki.ros.org/buildfarm/Pull%20request%20testing'
                  )
            return False
    else:
        print(
            'ERROR: No github repository found at %s/%s' % (args.user, args.repo)
        )
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Test for ros-pull-request-builder access')
    parser.add_argument('user', type=str)
    parser.add_argument('repo', type=str)
    parser.add_argument('--callback-url', type=str,
        default='http://build.ros.org/ghprbhook/')
    parser.add_argument('--hook-user', type=str,
        default='ros-pull-request-builder')
    parser.add_argument('--password-env', type=str,
        default='ROSGHPRB_TOKEN')

    args = parser.parse_args()

    password = os.getenv(args.password_env)
    if not password:
        parser.error(
            'OAUTH Token with hook and organization read access'
            'required in ROSGHPRB_TOKEN environment variable')
    errors = []
    result = check_hooks_on_repo(
        args.user,
        args.repo,
        errors,
        args.hook_user,
        args.callback_url,
        password)
    for e in errors:
        print(e)
    return result


if __name__ == '__main__':
    sys.exit(main() == False)
