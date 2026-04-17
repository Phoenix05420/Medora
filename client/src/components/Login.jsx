import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import axios from 'axios';

const Login = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Use the backend URL
  const API_BASE = "http://localhost:8000";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // FastAPI OAuth2PasswordRequestForm uses form data
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      const res = await axios.post(`${API_BASE}/auth/login`, formData);
      const { access_token } = res.data;
      
      onLogin({ 
        name: email.split('@')[0], 
        email, 
        access_token 
      });
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed. Check your data.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    setError('');
    setLoading(true);
    try {
      const { credential } = credentialResponse;
      const res = await axios.post(`${API_BASE}/auth/google`, { token: credential });
      const { access_token } = res.data;
      
      // In a real app we'd decode the JWT to get the name
      onLogin({ 
        name: "Google User", 
        email: "google-user@example.com", 
        access_token 
      });
    } catch (err) {
      setError("Google Login failed. Please try again.");
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
              <h2 className="fw-bold tracking-tight">Sign In</h2>
              <p className="text-secondary">Access your secure medical vault.</p>
            </div>
            
            {error && (
              <div className="alert alert-danger py-2 small mb-4" role="alert">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-4">
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
                  {loading ? 'Processing...' : 'Sign In'}
                </button>
              </div>

              <div className="text-center py-3">
                <div className="position-relative">
                  <hr className="text-muted" />
                  <span className="position-absolute top-50 start-50 translate-middle bg-white px-3 text-muted small uppercase">OR</span>
                </div>
              </div>

              {/* Demo Login — instant access for testing */}
              <div className="d-grid mb-3">
                <button 
                  type="button"
                  onClick={() => {
                    onLogin({ 
                      name: 'Demo User', 
                      email: 'demo@smartmedical.app', 
                      access_token: 'demo-token-for-testing' 
                    });
                  }}
                  className="btn btn-outline-success btn-lg py-3 fw-bold rounded-pill"
                >
                  <i className="bi bi-lightning-charge-fill me-2"></i>
                  Quick Demo Login
                </button>
                <p className="text-muted mt-2 mb-0" style={{fontSize: '0.7rem'}}>
                  Skip authentication and explore the OCR features instantly
                </p>
              </div>

              {/* Google OAuth Button — only if properly configured */}
              <div className="d-flex justify-content-center mt-2">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={() => {}} 
                  theme="filled_blue"
                  shape="pill"
                  width="100%"
                />
              </div>
            </form>

            <div className="mt-4 pt-4 border-top d-flex justify-content-between x-small text-muted">
              <a href="#" className="text-decoration-none text-muted hover:text-primary">Forgot password?</a>
              <a href="#" className="text-decoration-none text-muted hover:text-primary">Create an account</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
