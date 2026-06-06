import { app, BrowserWindow } from 'electron';
import path from 'path';
import { spawn, ChildProcess } from 'child_process';
import { fileURLToPath } from 'url';

// FIX: Define __dirname for ES Modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Keep a global reference of the window object to avoid garbage collection
let win: BrowserWindow | null = null;
let pythonProcess: ChildProcess | null = null;
const isDev = !app.isPackaged;

function startPythonBackend() {
  console.log('Starting Python Backend...');
  
  // Calculate project root: 
  // We are in frontend/dist-electron/main.js -> go up two levels to get to project root in dev
  // When packaged, Electron resources are under process.resourcesPath/app (see electron-builder config)
  const projectRoot = isDev 
    ? path.join(__dirname, '../../') 
    : path.join(process.resourcesPath, 'app'); 
  console.log('Project Root:', projectRoot);

  // Check if we are in a venv (heuristic) or just default to python3
  const pythonCmd = 'python3'; 
  
  // Spawn the python process
  pythonProcess = spawn(pythonCmd, ['-m', 'app.backend_server'], {
    cwd: projectRoot,
    stdio: 'inherit', // Pipe output to console
    shell: true       // Use shell to pick up environment variables if possible
  });

  pythonProcess.on('error', (err) => {
    console.error('Failed to start python process:', err);
  });
  
  pythonProcess.on('exit', (code, signal) => {
    console.log(`Python process exited with code ${code} and signal ${signal}`);
  });
}

function createWindow() {
  win = new BrowserWindow({
    width: 1280,
    height: 900,
    backgroundColor: '#0f172a',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      webSecurity: false,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  if (process.env.VITE_DEV_SERVER_URL) {
    win.loadURL(process.env.VITE_DEV_SERVER_URL);
  } else {
    win.loadFile(path.join(__dirname, '../dist/index.html'));
  }
}

app.whenReady().then(() => {
  startPythonBackend();
  setTimeout(createWindow, 1000); 
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  if (pythonProcess) {
    console.log('Killing Python Backend...');
    pythonProcess.kill();
    pythonProcess = null;
  }
});
