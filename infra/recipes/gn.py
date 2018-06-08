# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.
"""Recipe for building GN."""

DEPS = [
    'recipe_engine/buildbucket',
    'recipe_engine/cipd',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]


def RunSteps(api):
  src_dir = api.path['start_dir'].join('gn')

  with api.step.nest('git'), api.context(infra_steps=True):
    api.step('init', ['git', 'init', src_dir])

    with api.context(cwd=src_dir):
      build_input = api.buildbucket.build_input
      if build_input.gerrit_changes:
        for change in build_input.gerrit_changes:
          api.step('fetch', [
              'git', 'fetch',
              'https://%s/gn' % change.host,
              'refs/changes/%s/%s/%s' %
              (str(change.change)[-2:], change.change, change.patchset)
          ])
          api.step('cherry-pick', ['git', 'cherry-pick', 'FETCH_HEAD'])
      else:
        ref = (
            build_input.gitiles_commit.id
            if build_input.gitiles_commit else 'refs/heads/master')
        api.step('fetch',
                 ['git', 'fetch', 'https://gn.googlesource.com/gn', ref])
        api.step('checkout', ['git', 'checkout', 'FETCH_HEAD'])

  with api.context(infra_steps=True):
    cipd_dir = api.path['start_dir'].join('cipd')
    packages = {
      'infra/ninja/${platform}': 'version:1.8.2',
    }
    api.cipd.ensure(cipd_dir, packages)

  with api.context(env_prefixes={'PATH': [cipd_dir]}):
    api.python(
        'bootstrap',
        src_dir.join('tools', 'gn', 'bootstrap', 'bootstrap.py'),
        args=['--no-rebuild'])


def GenTests(api):
  for platform in ('linux', 'mac', 'win'):
    yield (api.test('ci_' + platform) + api.platform.name(platform) +
           api.properties(buildbucket={
               'build': {
                   'tags': [
                       'buildset:commit/gitiles/gn.googlesource.com/gn/+/'
                       'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                   ]
               }
           }))
    yield (
        api.test('cq_' + platform) + api.platform.name(platform) +
        api.properties(buildbucket={
            'build': {
                'tags': [
                    'buildset:patch/gerrit/gn-review.googlesource.com/1000/1',
                ]
            }
        }))