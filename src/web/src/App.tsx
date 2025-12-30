import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useCrypto } from './hooks/useCrypto';
import { Upload } from './pages/Upload';
import { Download } from './pages/Download';
import { Share } from './pages/Share';

export default function App() {
  const { isReady, error } = useCrypto();
  
  if (error) {
    return (
      <div style={{ maxWidth: '600px', margin: '50px auto', padding: '20px' }}>
        <h1>Error</h1>
        <p>Failed to load cryptography module: {error}</p>
      </div>
    );
  }
  
  if (!isReady) {
    return (
      <div style={{ maxWidth: '600px', margin: '50px auto', padding: '20px', textAlign: 'center' }}>
        <h1>Loading...</h1>
        <p>Initializing cryptography module (WASM)</p>
      </div>
    );
  }
  
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Upload />} />
        <Route path="/download" element={<Download />} />
        <Route path="/share" element={<Share />} />
      </Routes>
    </BrowserRouter>
  );
}
