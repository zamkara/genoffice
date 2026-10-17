"""Wire GenOffice's in-app updater on Arch Linux / Omarchy to zamkara/genoffice releases."""
import pathlib,sys

ARCH_UPDATER_BLOCK = """import { execFileSync, spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { EventEmitter } from 'node:events'
import { createWriteStream, existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs'
import https from 'node:https'
import os from 'node:os'
import path from 'node:path'
import { app, dialog, shell } from 'electron'
import type { BrowserWindow } from 'electron'
import { autoUpdater as electronAutoUpdater, CancellationToken } from 'electron-updater'
import { installResumeDownload } from './update-resume'
import type { UpdateInfo } from 'electron-updater'

const ARCH_REPOSITORY = '@REPOSITORY@'
const ARCH_RELEASES_LATEST_URL = `https://github.com/${ARCH_REPOSITORY}/releases/latest`
const ARCH_API_LATEST_URL = `https://api.github.com/repos/${ARCH_REPOSITORY}/releases/latest`
const isArchLinuxNative = process.platform === 'linux' && !process.env.APPIMAGE

function currentArchVersion(): string {
  try {
    const out = execFileSync('pacman', ['-Q', 'genoffice'], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim()
    const parts = out.split(/\\s+/)
    if (parts[1]) return parts[1]
  } catch {}
  try {
    const raw = readFileSync(path.join(process.resourcesPath, 'arch-release.json'), 'utf8')
    const meta = JSON.parse(raw) as { version?: string }
    if (typeof meta.version === 'string' && meta.version) return meta.version
  } catch {}
  return app.getVersion()
}

function httpsGetBuffer(url: string, headers: Record<string, string> = {}, redirects = 5): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    if (redirects < 0) {
      reject(new Error('Too many redirects'))
      return
    }
    const req = https.get(
      url,
      {
        headers: {
          'User-Agent': 'GenOffice-ArchLinux-Updater',
          ...headers,
        },
        timeout: 30_000,
      },
      (res) => {
        const code = res.statusCode ?? 0
        if ([301, 302, 303, 307, 308].includes(code) && res.headers.location) {
          res.resume()
          const nextUrl = new URL(res.headers.location, url).toString()
          httpsGetBuffer(nextUrl, headers, redirects - 1).then(resolve, reject)
          return
        }
        if (code < 200 || code >= 300) {
          res.resume()
          reject(new Error(`HTTP ${code} for ${url}`))
          return
        }
        const chunks: Buffer[] = []
        res.on('data', (chunk: Buffer) => chunks.push(chunk))
        res.on('end', () => resolve(Buffer.concat(chunks)))
        res.on('error', reject)
      },
    )
    req.on('timeout', () => req.destroy(new Error('Request timed out')))
    req.on('error', reject)
  })
}

function httpsDownloadFile(
  url: string,
  destPath: string,
  expectedSize: number,
  token: CancellationToken | undefined,
  onProgress: (percent: number) => void,
  redirects = 5,
): Promise<string> {
  return new Promise((resolve, reject) => {
    if (redirects < 0) {
      reject(new Error('Too many redirects'))
      return
    }
    const req = https.get(
      url,
      {
        headers: { 'User-Agent': 'GenOffice-ArchLinux-Updater' },
        timeout: 60_000,
      },
      (res) => {
        const code = res.statusCode ?? 0
        if ([301, 302, 303, 307, 308].includes(code) && res.headers.location) {
          res.resume()
          const nextUrl = new URL(res.headers.location, url).toString()
          httpsDownloadFile(nextUrl, destPath, expectedSize, token, onProgress, redirects - 1).then(
            resolve,
            reject,
          )
          return
        }
        if (code < 200 || code >= 300) {
          res.resume()
          reject(new Error(`HTTP ${code} downloading package`))
          return
        }
        const total = Number(res.headers['content-length']) || expectedSize || 0
        const hash = createHash('sha256')
        const out = createWriteStream(destPath, { mode: 0o600 })
        let received = 0
        const checkCancel = (): boolean => {
          if ((token as unknown as { cancelled?: boolean })?.cancelled) {
            req.destroy(new Error('Download cancelled'))
            out.destroy()
            return true
          }
          return false
        }
        res.on('data', (chunk: Buffer) => {
          if (checkCancel()) return
          hash.update(chunk)
          received += chunk.length
          if (total > 0) {
            onProgress(Math.min(99, (received / total) * 100))
          }
        })
        res.pipe(out)
        out.on('finish', () => {
          out.close(() => resolve(hash.digest('hex')))
        })
        out.on('error', reject)
        res.on('error', reject)
      },
    )
    req.on('timeout', () => req.destroy(new Error('Download timed out')))
    req.on('error', reject)
  })
}

interface ArchReleaseMetadata {
  version: string
  pkgName: string
  pkgUrl: string
  sumsUrl: string
  size: number
}

class ArchLinuxAutoUpdater extends EventEmitter {
  channel: string | null = 'latest'
  allowDowngrade = false
  autoDownload = false
  autoInstallOnAppQuit = true
  disableDifferentialDownload = true
  private latestRelease: ArchReleaseMetadata | null = null
  private downloadedPkgPath: string | null = null

  async checkForUpdates(): Promise<{ isUpdateAvailable: boolean; updateInfo: UpdateInfo }> {
    const raw = await httpsGetBuffer(ARCH_API_LATEST_URL, {
      Accept: 'application/vnd.github+json',
    })
    const release = JSON.parse(raw.toString('utf8')) as {
      draft?: boolean
      assets?: Array<{ name?: string; browser_download_url?: string; size?: number }>
    }
    const assets = release.assets ?? []
    const pkgAsset = assets.find(
      (a) =>
        typeof a.name === 'string' &&
        a.name.startsWith('genoffice-') &&
        a.name.endsWith('-x86_64.pkg.tar.zst') &&
        typeof a.browser_download_url === 'string',
    )
    const sumsAsset = assets.find(
      (a) => a.name === 'SHA256SUMS' && typeof a.browser_download_url === 'string',
    )
    if (!pkgAsset?.name || !pkgAsset.browser_download_url || !sumsAsset?.browser_download_url) {
      throw new Error('Latest Arch Linux release is missing package or SHA256SUMS assets')
    }
    const remoteVersion = pkgAsset.name.slice('genoffice-'.length, -'-x86_64.pkg.tar.zst'.length)
    const current = currentArchVersion()
    const cmpOut = execFileSync('vercmp', [current, remoteVersion], { encoding: 'utf8' }).trim()
    const isUpdateAvailable = Number(cmpOut) < 0
    this.latestRelease = {
      version: remoteVersion,
      pkgName: pkgAsset.name,
      pkgUrl: pkgAsset.browser_download_url,
      sumsUrl: sumsAsset.browser_download_url,
      size: Number(pkgAsset.size) || 0,
    }
    const info = {
      version: remoteVersion,
      files: [{ url: pkgAsset.browser_download_url }],
    } as unknown as UpdateInfo
    if (isUpdateAvailable) {
      this.emit('update-available', info)
    }
    return { isUpdateAvailable, updateInfo: info }
  }

  async downloadUpdate(cancellationToken?: CancellationToken): Promise<string[]> {
    const rel = this.latestRelease
    if (!rel) throw new Error('No Arch Linux update metadata available')
    const workDir = mkdtempSync(path.join(os.tmpdir(), 'genoffice-arch-update-'))
    try {
      const sumsRaw = await httpsGetBuffer(rel.sumsUrl)
      const expectedSha = sumsRaw
        .toString('utf8')
        .split(/\\r?\\n/)
        .map((line) => line.trim().split(/\\s+/))
        .find((parts) => parts.length === 2 && parts[1] === rel.pkgName)?.[0]
      if (!expectedSha || !/^[a-f0-9]{64}$/i.test(expectedSha)) {
        throw new Error(`Missing SHA-256 checksum for ${rel.pkgName}`)
      }
      const pkgPath = path.join(workDir, rel.pkgName)
      const actualSha = await httpsDownloadFile(
        rel.pkgUrl,
        pkgPath,
        rel.size,
        cancellationToken,
        (percent) => this.emit('download-progress', { percent }),
      )
      if (actualSha.toLowerCase() !== expectedSha.toLowerCase()) {
        throw new Error('Downloaded package SHA-256 checksum mismatch')
      }
      this.downloadedPkgPath = pkgPath
      const info = {
        version: rel.version,
        files: [{ url: rel.pkgUrl }],
      } as unknown as UpdateInfo
      this.emit('update-downloaded', info)
      return [pkgPath]
    } catch (err) {
      try {
        rmSync(workDir, { recursive: true, force: true })
      } catch {}
      this.emit('error', err)
      throw err
    }
  }

  quitAndInstall(_isSilent?: boolean, _isForceRunAfter?: boolean): void {
    const pkgPath = this.downloadedPkgPath
    if (!pkgPath || !existsSync(pkgPath)) {
      void shell.openExternal(ARCH_RELEASES_LATEST_URL)
      return
    }
    const child = spawn('pkexec', ['pacman', '-U', '--noconfirm', '--', pkgPath], {
      stdio: 'ignore',
    })
    child.on('error', () => {
      void shell.openExternal(ARCH_RELEASES_LATEST_URL)
    })
    child.on('exit', (code) => {
      if (code === 0) {
        try {
          rmSync(path.dirname(pkgPath), { recursive: true, force: true })
        } catch {}
        app.relaunch()
        app.exit(0)
      } else {
        void shell.openExternal(ARCH_RELEASES_LATEST_URL)
      }
    })
  }
}

const autoUpdater: typeof electronAutoUpdater = isArchLinuxNative
  ? (new ArchLinuxAutoUpdater() as unknown as typeof electronAutoUpdater)
  : electronAutoUpdater"""

def patch_file(target_path: pathlib.Path, repository: str = 'zamkara/genoffice') -> None:
    text = target_path.read_text(encoding='utf-8')
    old_imports = """import { readFileSync } from 'node:fs'
import path from 'node:path'
import { app, dialog, shell } from 'electron'
import type { BrowserWindow } from 'electron'
import { autoUpdater, CancellationToken } from 'electron-updater'
import { installResumeDownload } from './update-resume'
import type { UpdateInfo } from 'electron-updater'"""
    if old_imports not in text:
        raise SystemExit('Could not find expected import block in apps/shell/src/main/updater.ts')
    text = text.replace(old_imports, ARCH_UPDATER_BLOCK.replace('@REPOSITORY@', repository), 1)

    old_download_url = "const DOWNLOAD_PAGE_URL = 'https://github.com/genspark-ai/genoffice/releases/latest'"
    new_download_url = "const DOWNLOAD_PAGE_URL = isArchLinuxNative ? ARCH_RELEASES_LATEST_URL : 'https://github.com/genspark-ai/genoffice/releases/latest'"
    if old_download_url not in text:
        raise SystemExit('Could not find DOWNLOAD_PAGE_URL in apps/shell/src/main/updater.ts')
    text = text.replace(old_download_url, new_download_url, 1)

    old_curr_ver = "currentVersion: app.getVersion(),"
    new_curr_ver = "currentVersion: isArchLinuxNative ? currentArchVersion() : app.getVersion(),"
    if old_curr_ver not in text:
        raise SystemExit('Could not find currentVersion in apps/shell/src/main/updater.ts')
    text = text.replace(old_curr_ver, new_curr_ver, 1)

    old_uptodate = "message: tUpd(lang, 'updUpToDate', { version: app.getVersion() }),"
    new_uptodate = "message: tUpd(lang, 'updUpToDate', { version: isArchLinuxNative ? currentArchVersion() : app.getVersion() }),"
    if old_uptodate not in text:
        raise SystemExit('Could not find updUpToDate message in apps/shell/src/main/updater.ts')
    text = text.replace(old_uptodate, new_uptodate, 1)

    old_guard = """  const isLinuxAppImage = process.platform === 'linux' && Boolean(process.env.APPIMAGE)
  if (process.platform !== 'win32' && process.platform !== 'darwin' && !isLinuxAppImage) return"""
    new_guard = """  const isLinuxAppImage = process.platform === 'linux' && Boolean(process.env.APPIMAGE)
  if (process.platform !== 'win32' && process.platform !== 'darwin' && !isLinuxAppImage && !isArchLinuxNative) return"""
    if old_guard not in text:
        raise SystemExit('Could not find platform guard in apps/shell/src/main/updater.ts')
    text = text.replace(old_guard, new_guard, 1)

    old_resume = "  installResumeDownload(autoUpdater as unknown as Parameters<typeof installResumeDownload>[0])"
    new_resume = "  if (!isArchLinuxNative) installResumeDownload(autoUpdater as unknown as Parameters<typeof installResumeDownload>[0])"
    if old_resume not in text:
        raise SystemExit('Could not find installResumeDownload in apps/shell/src/main/updater.ts')
    text = text.replace(old_resume, new_resume, 1)

    target_path.write_text(text, encoding='utf-8')

if __name__ == '__main__':
    repo = sys.argv[2] if len(sys.argv) > 2 else 'zamkara/genoffice'
    patch_file(pathlib.Path(sys.argv[1]), repo)
