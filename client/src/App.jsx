import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import { SignedIn, SignedOut, SignIn } from '@clerk/clerk-react';

function App() {
  const [showEmergency, setShowEmergency] = useState(false);


  if (showEmergency) {
    return (
      <div className="vh-100 bg-danger d-flex flex-column align-items-center justify-content-center p-4 text-white text-center">
        <h1 className="display-1 fw-black mb-4 animate-pulse">EMERGENCY MODE</h1>
        <div className="card glass-card text-dark w-100 shadow-lg" style={{maxWidth: '450px'}}>
          <div className="card-body p-4">
            <h2 className="h4 fw-bold mb-4 border-bottom pb-2">Patient Emergency Profile</h2>
            <div className="text-start">
              <div className="mb-3">
                <label className="text-muted x-small fw-bold text-uppercase">Blood Group</label>
                <p className="h5 fw-bold text-danger">O Positive (O+)</p>
              </div>
              <div className="mb-3">
                <label className="text-muted x-small fw-bold text-uppercase">Emergency Contact</label>
                <p className="h5 fw-bold">+1 (555) 012-3456 (Spouse)</p>
              </div>
              <div className="mb-1">
                <label className="text-muted x-small fw-bold text-uppercase">Medical Conditions</label>
                <ul className="list-unstyled fw-semibold text-danger">
                  <li>• Chronic Hypertension</li>
                  <li>• Severe Penicillin Allergy</li>
                </ul>
              </div>
            </div>
            <button 
              onClick={() => setShowEmergency(false)}
              className="btn btn-dark w-100 py-3 mt-4 fw-bold rounded-pill"
            >
              Exit Emergency Mode
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-vh-100 bg-light d-flex flex-column">
      <Navbar onEmergency={() => setShowEmergency(true)} />
      
      <main className="flex-grow-1">
        <SignedOut>
          <div className="container mt-5 py-5 d-flex justify-content-center">
             <SignIn routing="hash" />
          </div>
        </SignedOut>
        
        <SignedIn>
          <Dashboard />
        </SignedIn>
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
