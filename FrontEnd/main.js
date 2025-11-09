// C:\Users\Aluno\DSMTerceiro\ProjetoHackathon\FrontEnd\main.js

const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
  // Configurações críticas para o modo 'Overlay'
  mainWindow = new BrowserWindow({
    width: 800, 
    height: 150,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false, 
      // ignoreMouseEvents removed from webPreferences: use setIgnoreMouseEvents on the window instance instead
    }
  });

  mainWindow.loadFile('index.html');
  

  // Mouse-events behavior will be controlled from the renderer process
  // based on where the cursor is (transparent vs opaque areas).

  //mainWindow.webContents.openDevTools();

}

// --- OUvinte de Comunicação (IPC Main) ---
// Este ouvinte permite que o frontend (index.html) altere o estado do mouse
ipcMain.on('set-ignore-mouse-events', (event, ignore, options) => {
  if (mainWindow) {
    mainWindow.setIgnoreMouseEvents(ignore, options);
  }
});
// ----------------------------------------

// Listener to close the app from renderer
ipcMain.on('app-close', () => {
  if (mainWindow) {
    mainWindow.close();
  }
});

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});