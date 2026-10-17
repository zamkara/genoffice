import json,pathlib,tempfile,unittest
from unittest.mock import patch
import prepare

class PlanningTests(unittest.TestCase):
    def test_identical_published_inputs_skip(self):
        state={'commit':'a'*40,'recipe_sha256':'c'*64}
        self.assertTrue(prepare.same_inputs(dict(state),state))
        self.assertFalse(prepare.same_inputs(None,state))
        for key in state:
            changed=dict(state);changed[key]='different'
            self.assertFalse(prepare.same_inputs(state,changed))

    def test_skip_happens_before_source_download_or_changelog_fetch(self):
        commit='a'*40;recipe='b'*64
        old={'app':'genoffice','commit':commit,'recipe_sha256':recipe}
        def api(path):
            if path=='repos/genspark-ai/genoffice':return {'default_branch':'main'}
            if path=='repos/genspark-ai/genoffice/commits/main':return {'sha':commit,'commit':{'committer':{'date':'2026-10-17T04:02:54Z'}}}
            raise AssertionError('Unexpected request: '+path)
        def content(repo,path,sha):
            return '{"version":"0.11.0"}\n' if path=='apps/shell/package.json' else ''
        with tempfile.TemporaryDirectory() as directory,patch('sys.argv',['prepare.py','--directory',directory]),patch.object(prepare,'api',api),patch.object(prepare,'content',content),patch.object(prepare,'recipe_hash',return_value=recipe),patch.object(prepare,'previous',return_value=old),patch.object(prepare,'download_archive') as archive,patch.object(prepare,'notes') as notes,patch.object(prepare,'output') as output:
            prepare.main();archive.assert_not_called();notes.assert_not_called()
            self.assertEqual(output.call_args.args[0]['changed'],'false')

    def test_changed_upstream_generates_pkgbuild_and_installer(self):
        commit='a'*40;recipe='b'*64
        def api(path):
            if path=='repos/genspark-ai/genoffice':return {'default_branch':'main'}
            if path=='repos/genspark-ai/genoffice/commits/main':return {'sha':commit,'commit':{'committer':{'date':'2026-10-17T04:02:54Z'}}}
            raise AssertionError('Unexpected request: '+path)
        def content(repo,path,sha):
            return '{"version":"0.11.0"}\n'
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory)
            with patch('sys.argv',['prepare.py','--directory',directory]),patch.object(prepare,'api',api),patch.object(prepare,'content',content),patch.object(prepare,'recipe_hash',return_value=recipe),patch.object(prepare,'previous',return_value=None),patch.object(prepare,'download_archive',return_value=('genoffice.tar.gz::https://example.com','d'*64)),patch.object(prepare,'notes',return_value='Release notes\n'),patch.object(prepare,'output') as output:
                prepare.main()
                self.assertEqual(output.call_args.args[0]['changed'],'true')
                self.assertTrue((root/'PKGBUILD').is_file())
                self.assertTrue((root/'install.sh').is_file())
                self.assertIn('genoffice-0.11.0.r20261017040254.gaaaaaaaaaaaa-1',(root/'install.sh').read_text())

    def test_snapshot_version_is_reproducible(self):
        self.assertEqual(prepare.pkgversion('0.11.0','2026-10-17T04:02:54Z','a'*40),'0.11.0.r20261017040254.gaaaaaaaaaaaa')

    def test_changelog_preserves_upstream_commit_messages(self):
        message='fix(ai): give every Gemini tool-schema array an items (#2067)'
        with patch.object(prepare,'api',return_value={'commits':[{'commit':{'message':message},'html_url':'https://github.com/genspark-ai/genoffice/commit/abc'}]}):
            self.assertIn(message,prepare.changes('genspark-ai/genoffice','abc','def'))

if __name__=='__main__':unittest.main()
