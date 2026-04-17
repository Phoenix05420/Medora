import React from 'react';
import { UserButton, SignedIn, SignedOut } from '@clerk/clerk-react';

const Navbar = ({ onEmergency }) => {
  return (
    <nav className="navbar navbar-expand-lg glass-card sticky-top mx-3 mt-2 py-3 px-4">
      <div className="container-fluid">
        <div className="navbar-brand d-flex align-items-center">
          <div className="bg-primary rounded text-white px-2 py-1 fw-bold me-2">M</div>
          <span className="fw-bold tracking-tight text-primary">Medora</span>
        </div>
        
        <div className="d-flex align-items-center gap-3">
          <button 
            onClick={onEmergency}
            className="btn btn-danger btn-sm rounded-pill px-3 py-1 fw-bold emergency-btn shadow-sm"
          >
            Emergency Access
          </button>
          
          <SignedIn>
            <div className="d-flex align-items-center gap-3">
              <UserButton afterSignOutUrl="/" />
            </div>
          </SignedIn>
          <SignedOut>
            <span className="text-muted small">Secure Vault</span>
          </SignedOut>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
