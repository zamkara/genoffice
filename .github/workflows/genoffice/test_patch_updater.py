import pathlib,tempfile,unittest
import patch_updater

SAMPLE_UPDATER = """import { readFileSync } from 'node:fs'
import path from 'node:path'
import { app, dialog, shell } from 'electron'
import type { BrowserWindow } from 'electron'
import { autoUpdater, CancellationToken } from 'electron-updater'
import { installResumeDownload } from './update-resume'
import type { UpdateInfo } from 'electron-updater'

const DOWNLOAD_PAGE_URL = 'https://github.com/genspark-ai/genoffice/releases/latest'

function initialState(version: string) {
  return {
    version,
    currentVersion: app.getVersion(),
  }
}

export async function checkForUpdatesNow() {
  const msg = {
    message: tUpd(lang, 'updUpToDate', { version: app.getVersion() }),
  }
}

export function initAutoUpdater() {
  if (!app.isPackaged) return
  const isLinuxAppImage = process.platform === 'linux' && Boolean(process.env.APPIMAGE)
  if (process.platform !== 'win32' && process.platform !== 'darwin' && !isLinuxAppImage) return
  installResumeDownload(autoUpdater as unknown as Parameters<typeof installResumeDownload>[0])
}
"""

class PatchUpdaterTests(unittest.TestCase):
    def test_patch_wires_arch_linux_updater(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / 'updater.ts'
            path.write_text(SAMPLE_UPDATER, encoding='utf-8')
            patch_updater.patch_file(path, 'zamkara/genoffice')
            patched = path.read_text(encoding='utf-8')
            self.assertIn("const ARCH_REPOSITORY = 'zamkara/genoffice'", patched)
            self.assertIn('class ArchLinuxAutoUpdater extends EventEmitter', patched)
            self.assertIn('!isLinuxAppImage && !isArchLinuxNative', patched)
            self.assertIn('if (!isArchLinuxNative) installResumeDownload', patched)
            self.assertIn("spawn('pkexec', ['pacman', '-U', '--noconfirm', '--', pkgPath]", patched)

if __name__ == '__main__':
    unittest.main()
