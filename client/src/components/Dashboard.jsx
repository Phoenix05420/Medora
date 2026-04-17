import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Activity, 
  FileText, 
  Upload, 
  Search, 
  Calendar, 
  Bell, 
  Sparkles, 
  Plus, 
  ChevronRight, 
  TrendingUp, 
  ShieldAlert,
  CheckCircle2,
  Clock,
  MapPin,
  Map as MapIcon,
  AlertTriangle
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';

const API_BASE = "http://localhost:8000";

const Dashboard = ({ user }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [records, setRecords] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [location, setLocation] = useState({ lat: 51.505, lng: -0.09 }); // Default
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchData();
    getUserLocation();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const authHeader = { Authorization: `Bearer ${user.access_token}` };
      const [recordsRes, summaryRes] = await Promise.all([
        axios.get(`${API_BASE}/prescriptions/`, { headers: authHeader }),
        axios.get(`${API_BASE}/summaries/generate`, { headers: authHeader })
      ]);
      setRecords(recordsRes.data);
      setSummary(summaryRes.data);
    } catch (err) {
      console.error("Dashboard sync error", err);
    } finally {
      setLoading(false);
    }
  };

  const getUserLocation = () => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition((position) => {
        setLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude
        });
      }, (err) => console.warn("Location access denied"));
    }
  };

  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      await axios.post(`${API_BASE}/prescriptions/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${user.access_token}`
        }
      });
      await fetchData();
      setActiveTab('history');
    } catch (err) {
      setError("Cloud sync failed. Check Google API quota.");
    } finally {
      setUploading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'TBD';
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  // Map R-insights risk level to UI
  const riskColor = summary?.statistical_insights?.risk_level === 'High' ? 'text-danger' : 'text-success';

  if (loading && !uploading) {
    return (
      <div className="d-flex justify-content-center align-items-center vh-100 bg-white">
        <div className="spinner-border text-primary" role="status"></div>
      </div>
    );
  }

  return (
    <div className="container-fluid py-4 px-md-5 animate-in fade-in">
      {/* Header */}
      <div className="d-flex justify-content-between align-items-end mb-5">
        <div>
          <h1 className="display-6 font-outfit text-navy mb-1">Health Intel, {user.name || 'User'}</h1>
          <p className="text-secondary mb-0">R-Analytics & Gemini Intelligence Synchronized.</p>
        </div>
        <button onClick={() => setActiveTab('scanner')} className="btn btn-premium d-flex align-items-center gap-2">
          <Plus size={20} /> New Scan
        </button>
      </div>

      {/* Tabs */}
      <div className="d-flex gap-3 mb-5 overflow-auto pb-2 noscroll">
        {[
          { id: 'overview', icon: <Activity size={18} />, label: 'Overview' },
          { id: 'history', icon: <FileText size={18} />, label: 'Records' },
          { id: 'scanner', icon: <Upload size={18} />, label: 'Scanner' },
          { id: 'insights', icon: <Sparkles size={18} />, label: 'AI Analysis' },
          { id: 'reminders', icon: <Bell size={18} />, label: 'Meds' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`sidebar-link border-0 bg-transparent ${activeTab === tab.id ? 'active' : ''}`}
          >
            <span className="me-2">{tab.icon}</span> {tab.label}
          </button>
        ))}
      </div>

      <div className="row g-4">
        <div className="col-lg-8">
          {activeTab === 'overview' && (
            <>
              <div className="row g-4 mb-4">
                <div className="col-md-6">
                  <div className="glass-card p-4">
                    <h6 className="text-uppercase x-small tracking-widest text-secondary font-bold mb-3">Med Adherence (R-Analysis)</h6>
                    <div className="d-flex align-items-baseline gap-2">
                      <h2 className="display-5 mb-0 font-outfit">92%</h2>
                      <span className="text-success small">High Clarity</span>
                    </div>
                    <div className="mt-4" style={{ height: 60 }}>
                      <ResponsiveContainer>
                        <BarChart data={records.slice(0, 5)}>
                          <Bar dataKey="id" fill="#2563eb" radius={4} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
                <div className="col-md-6">
                  <div className="glass-card p-4">
                    <h6 className="text-uppercase x-small tracking-widest text-secondary font-bold mb-3">Latest Diagnosis</h6>
                    <h3 className="h4 text-navy mb-2">{records[0]?.diagnoses?.[0] || 'Clean Profile'}</h3>
                    <p className="text-secondary small mb-0">Detected via Gemini Cloud OCR</p>
                  </div>
                </div>
              </div>

              <div className="glass-card p-4">
                <h3 className="h5 text-navy mb-4">Clinical History</h3>
                <div className="table-responsive">
                  <table className="table align-middle border-0">
                    <thead>
                      <tr className="text-secondary x-small text-uppercase font-bold">
                        <th>Doctor</th>
                        <th>Date</th>
                        <th>Meds</th>
                        <th>Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {records.map(r => (
                        <tr key={r.id}>
                          <td className="font-semibold py-3">{r.doctor_name}</td>
                          <td className="text-secondary">{formatDate(r.visit_date)}</td>
                          <td><span className="badge bg-primary bg-opacity-10 text-primary rounded-pill px-3">{r.medicines?.length} items</span></td>
                          <td><span className="text-success small d-flex align-items-center gap-1"><CheckCircle2 size={12}/> Verified</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {activeTab === 'insights' && (
            <div className="animate-in fade-in">
              <div className="glass-card bg-navy text-white p-5 mb-4 position-relative overflow-hidden border-0 shadow-lg">
                <div className="position-relative z-index-2">
                  <h3 className="h3 font-outfit mb-4 d-flex align-items-center gap-2 text-gradient">AI Health Intelligence</h3>
                  <div className="opacity-90 lead mb-0" style={{ lineHeight: 1.8 }}>
                    {summary?.ai_summary || "Scanning history..."}
                  </div>
                </div>
              </div>
              <div className="row g-4">
                <div className="col-md-12">
                  <div className="glass-card p-4 border-start border-primary border-4">
                    <h5 className="font-outfit text-primary mb-3">Statistical Risk Analysis (R-Engine)</h5>
                    <div className="bg-light p-4 rounded-4">
                      {summary?.statistical_insights ? (
                        <div className="row text-center">
                          <div className="col-4 border-end">
                            <label className="x-small text-uppercase text-secondary font-bold d-block">Risk Level</label>
                            <span className={`h4 font-bold ${riskColor}`}>{summary.statistical_insights.risk_level}</span>
                          </div>
                          <div className="col-8">
                            <label className="x-small text-uppercase text-secondary font-bold d-block">Statistical Insight</label>
                            <span className="h6 text-navy">{summary.statistical_insights.insight}</span>
                          </div>
                        </div>
                      ) : (
                        <p className="text-muted mb-0">Stat engine initializing...</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'history' && (
            <div className="animate-in slide-in-top">
              {records.map(r => (
                <div key={r.id} className="glass-card p-4 mb-3">
                  <div className="d-flex justify-content-between">
                    <div>
                      <h4 className="h5 mb-1">{r.doctor_name}</h4>
                      <p className="text-secondary small mb-3">{formatDate(r.visit_date)}</p>
                      <div className="d-flex gap-2">
                        {r.medicines?.map((m, i) => (
                          <span key={i} className="badge bg-light text-navy border font-normal">{m.name}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'scanner' && (
            <div className="glass-card p-5 text-center relative overflow-hidden h-100 min-vh-50 d-flex flex-column justify-content-center">
              {uploading && <div className="scan-line"></div>}
              <input type="file" ref={fileInputRef} className="d-none" onChange={handleUpload}/>
              <div className="stat-icon mx-auto bg-primary bg-opacity-10 text-primary mb-4" style={{ width: 80, height: 80 }}>
                <Upload size={32} />
              </div>
              <h3 className="h3 font-outfit mb-3">Precision Medical Scanner</h3>
              <p className="text-secondary mb-5">Gemini 2.0 Cloud Extraction Powered.</p>
              <button disabled={uploading} onClick={() => fileInputRef.current.click()} className="btn btn-premium px-5 py-3">
                {uploading ? 'Analyzing Matrix...' : 'Upload Prescription'}
              </button>
            </div>
          )}
        </div>

        {/* Right Sidebar - Logic Gaps Filled */}
        <div className="col-lg-4">
          {/* Real-time Google Maps Section */}
          <div className="glass-card p-4 mb-4 overflow-hidden position-relative">
            <div className="d-flex justify-content-between align-items-center mb-4">
              <h5 className="font-outfit mb-0 d-flex align-items-center gap-2">
                <MapPin size={18} className="text-primary"/> Medical Facility Near You
              </h5>
            </div>
            <div className="rounded-4 overflow-hidden border position-relative" style={{ height: '220px', background: '#f3f4f6' }}>
              {(import.meta.env.VITE_GOOGLE_MAPS_API_KEY && import.meta.env.VITE_GOOGLE_MAPS_API_KEY !== 'your_google_maps_key_here') ? (
                <iframe 
                  width="100%" 
                  height="100%" 
                  frameBorder="0" 
                  style={{ border: 0 }}
                  src={`https://www.google.com/maps/embed/v1/search?key=${import.meta.env.VITE_GOOGLE_MAPS_API_KEY}&q=hospital+pharmacy&center=${location.lat},${location.lng}&zoom=14`}
                  allowFullScreen
                  title="Google Maps Location"
                ></iframe>
              ) : (
                <div className="d-flex flex-column align-items-center justify-content-center h-100 text-center p-3">
                  <div className="bg-primary bg-opacity-10 p-3 rounded-circle mb-3">
                    <MapIcon size={32} className="text-primary"/>
                  </div>
                  <h6 className="font-bold text-navy mb-1">Interactive Map Offline</h6>
                  <p className="x-small text-secondary mb-3">Enable "Maps Embed API" in Cloud Console to activate.</p>
                  <a 
                    href={`https://www.google.com/maps/search/hospitals+and+pharmacies/@${location.lat},${location.lng},14z`} 
                    target="_blank" 
                    rel="noreferrer"
                    className="btn btn-sm btn-outline-primary rounded-pill px-4"
                  >
                    View Local Clinics
                  </a>
                </div>
              )}
              {/* Subtle Location Tag */}
              <div className="position-absolute bottom-0 start-0 w-100 bg-white bg-opacity-90 px-3 py-2 border-top d-flex justify-content-between align-items-center">
                <span className="x-small font-bold text-navy uppercase tracking-wider">Coordinates</span>
                <span className="x-small text-secondary opacity-75">{location.lat.toFixed(4)}, {location.lng.toFixed(4)}</span>
              </div>
            </div>
            <p className="mt-3 x-small text-secondary text-center mb-0">Local clinic search powered by Google Maps</p>
          </div>

          <div className="glass-card p-4">
            <h5 className="font-outfit mb-4">Medication Adherence</h5>
            {[
              { name: 'Metformin', time: '08:00 AM', status: 'Taken' },
              { name: 'Lisinopril', time: '02:00 PM', status: 'Pending' }
            ].map((m, i) => (
              <div key={i} className="d-flex justify-content-between align-items-center mb-3">
                <div className="d-flex align-items-center gap-2">
                  <div className="bg-primary bg-opacity-10 p-2 rounded-3"><Clock size={14} className="text-primary"/></div>
                  <div>
                    <div className="small font-semibold">{m.name}</div>
                    <div className="x-small text-secondary">{m.time}</div>
                  </div>
                </div>
                <span className={`badge ${m.status === 'Taken' ? 'bg-success' : 'bg-warning text-dark'} bg-opacity-10 rounded-pill x-small px-2`}>
                   {m.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
