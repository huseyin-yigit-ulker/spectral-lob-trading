import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import TradeLogs from './pages/TradeLogs';
import Screener from './pages/Screener';

function Navbar() {
  return (
    <nav className="bg-gray-800 border-b border-gray-700 p-4">
      <div className="container mx-auto flex gap-6 items-center">
        <h1 className="text-xl font-bold text-blue-400">Quant V5</h1>
        <div className="flex gap-4">
          <Link to="/" className="hover:text-blue-300">Dashboard</Link>
          <Link to="/trades" className="hover:text-blue-300">İşlemler (Trades)</Link>
          <Link to="/screener" className="hover:text-blue-300">İzci (Screener)</Link>
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-900 text-gray-100 font-sans">
        <Navbar />
        <main className="container mx-auto p-4">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/trades" element={<TradeLogs />} />
            <Route path="/screener" element={<Screener />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
