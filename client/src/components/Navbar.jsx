import React from 'react';

const Navbar = ({ user, setUser, onEmergency }) => {
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
          
          {user ? (
            <div className="d-flex align-items-center gap-3">
              <span className="text-secondary small">Hi, {user.name}</span>
              <button 
                onClick={() => setUser(null)}
                className="btn btn-link btn-sm text-decoration-none text-muted p-0"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <span className="text-muted small">Secure Vault</span>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
