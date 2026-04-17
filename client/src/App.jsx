import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import Login from './components/Login';
import AdminDashboard from './components/AdminDashboard';
import HospitalDashboard from './components/HospitalDashboard';
import EmergencyFlow from './components/EmergencyFlow';

function App() {
  const [user, setUser] = useState(null);
  const [showEmergency, setShowEmergency] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
    localStorage.setItem('token', userData.access_token);
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('user');
    localStorage.removeItem('token');
  };

  if (loading) {
    return (
      <div className="vh-100 d-flex align-items-center justify-content-center">
        <div className="spinner-border text-primary" role="status"></div>
      </div>
    );
  }

  if (showEmergency) {
    return <EmergencyFlow user={user} onClose={() => setShowEmergency(false)} />;
  }

  const renderDashboard = () => {
    if (user.role === 'admin') return <AdminDashboard user={user} />;
    if (user.role === 'hospital') return <HospitalDashboard user={user} />;
    return <Dashboard user={user} />;
  };



  return (
    <div className="min-vh-100 bg-light d-flex flex-column">
      <Navbar user={user} setUser={handleLogout} onEmergency={() => setShowEmergency(true)} />
      
      <main className="flex-grow-1">
        {!user ? (
          <Login onLogin={handleLogin} />
        ) : (
          renderDashboard()
        )}
      </main>

      <footer className="py-5 bg-white border-top mt-auto">
        <div className="container text-center text-muted small">
          <p className="mb-0">&copy; 2026 Smart Medical Record System. HIPPA Compliant & Secure.</p>
          <div className="mt-2 text-primary d-flex justify-content-center gap-3">
            <a href="#" className="text-decoration-none">Privacy</a>
            <a href="#" className="text-decoration-none">Terms</a>
            <a href="#" className="text-decoration-none">Support</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
