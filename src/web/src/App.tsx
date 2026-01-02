import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useCrypto } from './hooks/useCrypto';
import { Upload } from './pages/Upload';
import { Download } from './pages/Download';
import { Share } from './pages/Share';
import ErrorBoundary from './components/ErrorBoundary';

export default function App() {
  const { isReady, error } = useCrypto();

  if (error) {
    return (
      <div style={{ maxWidth: '600px', margin: '50px auto', padding: '20px' }}>
        <h1>Error</h1>
        <p>Failed to load cryptography module: {error}</p>
        <button
          onClick={() => window.location.reload()}
          style={{
            marginTop: '1rem',
            padding: '0.5rem 1rem',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Retry
        </button>
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
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/download" element={<Download />} />
          <Route path="/share" element={<Share />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
