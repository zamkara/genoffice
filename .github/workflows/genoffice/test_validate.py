import json,pathlib,tempfile,unittest
from unittest.mock import patch
import validate

class ValidateTests(unittest.TestCase):
    def test_validate_writes_package_and_checksums(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            pkg=root/'genoffice-0.11.0-1-x86_64.pkg.tar.zst'
            pkg.write_bytes(b'pkg-bytes')
            for name in ('install.sh','PKGBUILD','.SRCINFO'):
                (root/name).write_bytes(name.encode())
            (root/'upstream.json').write_text(json.dumps({'app':'genoffice'}))
            members='\n'.join([
                '.PKGINFO',
                '.BUILDINFO',
                'opt/GenOffice/genoffice',
                'opt/GenOffice/resources/app.asar',
                'opt/GenOffice/resources/cli/genoffice',
                'opt/GenOffice/resources/cli/genoffice.cjs',
                'opt/GenOffice/resources/native/xlsx-sidecar',
                'opt/GenOffice/resources/wasm/pdfium.wasm',
                'opt/GenOffice/resources/wasm/hb-subset.wasm',
                'usr/bin/genoffice',
                'usr/share/applications/genoffice.desktop',
                'usr/share/icons/hicolor/256x256/apps/genoffice.png',
                'usr/share/licenses/genoffice/LICENSE',
                'usr/share/licenses/genoffice/THIRD-PARTY-NOTICES.txt',
                *(f'opt/GenOffice/resources/modules/{m}/main/index.js' for m in validate.MODULES),
            ])
            with patch('subprocess.run'),patch('subprocess.check_output',return_value=members):
                validate.validate(root)
            state=json.loads((root/'upstream.json').read_text())
            self.assertEqual(state['package'],pkg.name)
            sums=(root/'SHA256SUMS').read_text()
            self.assertIn(pkg.name,sums)
            self.assertIn('install.sh',sums)

if __name__=='__main__':unittest.main()
