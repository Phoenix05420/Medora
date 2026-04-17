import React, { useState } from 'react';
import axios from 'axios';

const Login = ({ onLogin }) => {
  const [isRegistering, setIsRegistering] = useState(false);
  const [role, setRole] = useState('patient'); // patient, hospital
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Use the backend URL
  const API_BASE = "http://localhost:8000";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegistering) {
        await axios.post(`${API_BASE}/auth/register`, {
          email,
          password,
          name,
          role
        });
        setIsRegistering(false);
        setError('Registration successful. Please sign in.');
      } else {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);

        const res = await axios.post(`${API_BASE}/auth/login`, formData);
        const { access_token, role: userRole } = res.data;
        
        onLogin({ 
          name: email === 'admin@gmail.com' ? 'Admin' : email.split('@')[0], 
          email, 
          access_token,
          role: userRole
        });
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Authentication failed. Check your data.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mt-5 py-5">
      <div className="row justify-content-center">
        <div className="col-md-5">
          <div className="card glass-card border-0 p-4 shadow">
            <div className="text-center mb-4">
              <h2 className="fw-bold tracking-tight">{isRegistering ? 'Create Account' : 'Sign In'}</h2>
              <p className="text-secondary">Access your secure medical vault.</p>
            </div>
            
            {error && (
              <div className={`alert ${error.includes('successful') ? 'alert-success' : 'alert-danger'} py-2 small mb-4`} role="alert">
                {error}
              </div>
            )}

            {isRegistering && (
              <div className="d-flex justify-content-center gap-2 mb-4">
                <button 
                  type="button" 
                  className={`btn btn-sm ${role === 'patient' ? 'btn-primary' : 'btn-outline-primary'}`}
                  onClick={() => setRole('patient')}
                >Patient Mode</button>
                <button 
                  type="button" 
                  className={`btn btn-sm ${role === 'hospital' ? 'btn-success' : 'btn-outline-success'}`}
                  onClick={() => setRole('hospital')}
                >Hospital Mode</button>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              {isRegistering && (
                <div className="mb-3">
                  <label className="form-label fw-semibold small text-uppercase tracking-wider">Full Name / Hospital Name</label>
                  <input 
                    type="text" 
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="form-control form-control-lg border-light bg-light"
                    placeholder={role === 'patient' ? "John Doe" : "City General Hospital"}
                    required
                  />
                </div>
              )}
              
              <div className="mb-3">
                <label className="form-label fw-semibold small text-uppercase tracking-wider">Email Address</label>
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="form-control form-control-lg border-light bg-light"
                  placeholder="name@example.com"
                  required
                />
              </div>
              
              <div className="mb-4">
                <label className="form-label fw-semibold small text-uppercase tracking-wider">Password</label>
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="form-control form-control-lg border-light bg-light"
                  placeholder="••••••••"
                  required
                />
              </div>

              <div className="mb-4">
                <button 
                  type="submit" 
                  disabled={loading}
                  className="btn btn-primary btn-lg w-100 py-3 fw-bold shadow-sm"
                >
                  {loading ? 'Processing...' : (isRegistering ? 'Register' : 'Sign In')}
                </button>
              </div>

            </form>

            <div className="mt-4 pt-4 border-top text-center x-small text-muted">
              <button 
                type="button" 
                onClick={() => setIsRegistering(!isRegistering)}
                className="btn btn-link text-decoration-none text-primary fw-bold"
              >
                {isRegistering ? 'Already have an account? Sign In' : 'Create an account'}
              </button>
            </div>
            
            {/* Quick Demo Help */}
            <div className="text-center mt-2 small text-muted">
               Demo Admin: admin@gmail.com / admin@123
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;

