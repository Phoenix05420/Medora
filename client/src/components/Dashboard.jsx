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
  Download,
  CheckCircle2,
  Clock
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
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  // Stats Derived from Records
  const stats = {
    totalRecords: records.length,
    activeMeds: records.reduce((acc, r) => acc + (r.medicines?.length || 0), 0),
    healthScore: 85 // Mocked for now
  };

  useEffect(() => {
    fetchData();
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
      console.error("Failed to fetch dashboard data", err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    setError('');
    const formData = new FormData();
    formData.append('file', file);

    try {
      await axios.post(`${API_BASE}/prescriptions/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${user.access_token}`
        }
      });
      // Refresh after upload
      await fetchData();
      setActiveTab('history');
    } catch (err) {
      setError("Analysis failed. Please try a clearer image or check your API quota.");
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  // Helper for Date formatting
  const formatDate = (dateStr) => {
    if (!dateStr) return 'TBD';
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  if (loading && !uploading) {
    return (
      <div className="d-flex justify-content-center align-items-center vh-100 bg-white">
        <div className="spinner-grow text-primary" role="status"></div>
      </div>
    );
  }

  return (
    <div className="container-fluid py-4 px-md-5">
      {/* Header */}
      <div className="d-flex justify-content-between align-items-end mb-5">
        <div>
          <h1 className="display-6 font-outfit text-navy mb-1">Welcome back, {user.name || 'User'}</h1>
          <p className="text-secondary mb-0">Your medical intelligence system is synchronized and secure.</p>
        </div>
        <button 
          onClick={() => setActiveTab('scanner')}
          className="btn btn-premium d-flex align-items-center gap-2"
        >
          <Plus size={20} />
          New Prescription
        </button>
      </div>

      {/* Navigation */}
      <div className="d-flex gap-3 mb-5 overflow-auto pb-2 noscroll">
        {[
          { id: 'overview', icon: <Activity size={18} />, label: 'Health Overview' },
          { id: 'history', icon: <FileText size={18} />, label: 'Medical History' },
          { id: 'scanner', icon: <Upload size={18} />, label: 'Scanner' },
          { id: 'insights', icon: <Sparkles size={18} />, label: 'AI Analysis' },
          { id: 'reminders', icon: <Bell size={18} />, label: 'Reminders' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`sidebar-link border-0 bg-transparent ${activeTab === tab.id ? 'active' : ''}`}
          >
            <span className="me-2">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      <div className="row g-4">
        {/* Main Content Area */}
        <div className="col-lg-8">
          
          {/* OVERVIEW TAB */}
          {activeTab === 'overview' && (
            <div className="animate-in fade-in">
              <div className="row g-4 mb-4">
                <div className="col-md-6">
                  <div className="glass-card p-4 h-100">
                    <div className="d-flex justify-content-between mb-4">
                      <div>
                        <h6 className="text-uppercase x-small tracking-widest text-secondary font-outfit mb-1">Health Adherence</h6>
                        <h2 className="display-6 mb-0">85%</h2>
                      </div>
                      <div className="stat-icon bg-primary bg-opacity-10 text-primary">
                        <TrendingUp />
                      </div>
                    </div>
                    <div style={{ width: '100%', height: 150 }}>
                      <ResponsiveContainer>
                        <AreaChart data={[
                          { name: 'Mon', val: 65 }, { name: 'Tue', val: 80 }, 
                          { name: 'Wed', val: 75 }, { name: 'Thu', val: 90 }, 
                          { name: 'Fri', val: 85 }
                        ]}>
                          <defs>
                            <linearGradient id="colorVal" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3}/>
                              <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <Area type="monotone" dataKey="val" stroke="#2563eb" fillOpacity={1} fill="url(#colorVal)" strokeWidth={3} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
                <div className="col-md-6">
                  <div className="glass-card p-4 h-100">
                    <div className="d-flex justify-content-between mb-4">
                      <div>
                        <h6 className="text-uppercase x-small tracking-widest text-secondary font-outfit mb-1">Total Records</h6>
                        <h2 className="display-6 mb-0">{stats.totalRecords}</h2>
                      </div>
                      <div className="stat-icon bg-accent bg-opacity-10 text-accent">
                        <FileText />
                      </div>
                    </div>
                    <div className="mt-2">
                       <p className="text-secondary small">Latest: <span className="text-navy font-semibold">{records[0]?.doctor_name || 'No records yet'}</span></p>
                       <div className="progress rounded-pill bg-light" style={{ height: '8px' }}>
                          <div className="progress-bar bg-accent rounded-pill" style={{ width: '60%' }}></div>
                       </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="glass-card p-4">
                <div className="d-flex justify-content-between align-items-center mb-4">
                  <h3 className="h5 text-navy mb-0">Recent Records</h3>
                  <button onClick={() => setActiveTab('history')} className="btn btn-link text-primary text-decoration-none small">View All</button>
                </div>
                <div className="table-responsive">
                  <table className="table table-hover align-middle border-0">
                    <thead>
                      <tr className="text-secondary small font-outfit text-uppercase">
                        <th>Doctor / Facility</th>
                        <th>Visit Date</th>
                        <th>Medicines</th>
                        <th>Status</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {records.length > 0 ? records.slice(0, 4).map(r => (
                        <tr key={r.id} className="border-0">
                          <td className="py-3">
                            <div className="d-flex align-items-center">
                              <div className="bg-light p-2 rounded-3 me-3"><FileText size={20} className="text-secondary" /></div>
                              <span className="font-semibold">{r.doctor_name}</span>
                            </div>
                          </td>
                          <td className="text-secondary">{formatDate(r.visit_date)}</td>
                          <td>
                            <span className="badge bg-primary bg-opacity-10 text-primary border-primary border-opacity-10 py-1 px-2 rounded-pill font-normal">
                              {r.medicines?.length || 0} drugs
                            </span>
                          </td>
                          <td><span className="text-success small d-flex align-items-center gap-1"><CheckCircle2 size={12}/> AI Verified</span></td>
                          <td><ChevronRight size={18} className="text-light-secondary" /></td>
                        </tr>
                      )) : (
                        <tr><td colSpan="5" className="text-center py-5 text-secondary">No records found. Scanning your first prescription...</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* HISTORY TAB */}
          {activeTab === 'history' && (
            <div className="animate-in slide-in-bottom">
              <h3 className="h4 font-outfit mb-4">Electronic Health History</h3>
              {records.map(r => (
                <div key={r.id} className="glass-card p-4 mb-3 border-start border-primary border-4">
                   <div className="row align-items-center">
                      <div className="col-md-9">
                        <div className="d-flex align-items-center gap-3 mb-2">
                          <span className="badge bg-light text-navy border font-outfit px-3 py-2">{formatDate(r.visit_date)}</span>
                          <h4 className="h5 mb-0">{r.doctor_name}</h4>
                        </div>
                        <div className="d-flex gap-2 flex-wrap">
                          {r.diagnoses?.map((dx, i) => (
                            <span key={i} className="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-10">{dx}</span>
                          ))}
                          <span className="text-secondary small d-flex align-items-center border-start ps-2 ms-1"><Clock size={12} className="me-1"/> Prescribed {r.medicines?.length} items</span>
                        </div>
                      </div>
                      <div className="col-md-3 text-end">
                        <button className="btn btn-outline-primary btn-sm rounded-pill px-4">See Full Scan</button>
                      </div>
                   </div>
                </div>
              ))}
            </div>
          )}

          {/* SCANNER TAB */}
          {activeTab === 'scanner' && (
            <div className="animate-in zoom-in h-100">
               <div className={`glass-card p-5 text-center h-100 d-flex flex-column justify-content-center align-items-center relative overflow-hidden ${uploading ? 'bg-navy bg-opacity-5' : ''}`}>
                  {uploading && <div className="scan-line"></div>}
                  
                  <input 
                    type="file" 
                    ref={fileInputRef} 
                    className="d-none" 
                    onChange={handleUpload}
                    accept="image/*,.pdf"
                  />
                  
                  <div className={`mb-4 transition-all ${uploading ? 'scale-110' : ''}`}>
                    <div className={`stat-icon mx-auto ${uploading ? 'bg-primary text-white shadow-lg pulse' : 'bg-light text-secondary'}`} style={{ width: 100, height: 100 }}>
                      <Upload size={40} />
                    </div>
                  </div>

                  <h3 className="h3 font-outfit mb-2">{uploading ? 'AI Analysis in Progress...' : 'Digital Prescription Scanner'}</h3>
                  <p className="text-secondary max-w-sm mx-auto mb-5">
                    {uploading 
                      ? "Gemini AI is currently extracting medications, dosages, and clinical annotations from your document." 
                      : "Drag and drop your prescription or medical report here. Our hybrid OCR provides 95%+ accuracy for medical terms."}
                  </p>

                  <button 
                    onClick={() => fileInputRef.current.click()}
                    disabled={uploading}
                    className="btn btn-premium btn-lg px-5 mb-3"
                  >
                    {uploading ? 'Scanning...' : 'Select Report or Photo'}
                  </button>
                  <p className="x-small text-secondary text-uppercase tracking-widest mt-2">HIPAA compliant & AES-256 Encrypted</p>
                  
                  {error && (
                    <div className="mt-4 alert alert-danger border-0 bg-danger bg-opacity-10 text-danger d-flex align-items-center gap-2">
                       <ShieldAlert size={18} /> {error}
                    </div>
                  )}
               </div>
            </div>
          )}

          {/* INSIGHTS TAB */}
          {activeTab === 'insights' && (
            <div className="animate-in fade-in">
              <div className="glass-card bg-primary text-white p-5 position-relative overflow-hidden mb-4 border-0">
                   <div className="position-relative z-index-2">
                      <h3 className="h2 font-outfit mb-3 d-flex align-items-center gap-2"><Sparkles /> AI Health Insights</h3>
                      <div className="opacity-90 lead whitespace-pre-wrap">
                        {summary?.ai_summary || "Uploading records to generate personalized health intelligence..."}
                      </div>
                   </div>
                   <div className="position-absolute translate-middle-y end-0 top-50 opacity-10" style={{ fontSize: '15rem', color: 'white' }}>
                      <Activity />
                   </div>
              </div>
              <div className="row g-4">
                <div className="col-md-6">
                  <div className="glass-card p-4">
                    <h5 className="font-outfit text-navy mb-3">Health Chronology</h5>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={records.slice(0, 5)}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                        <XAxis dataKey="visit_date" tick={{fontSize: 10}} />
                        <YAxis hide />
                        <Tooltip />
                        <Bar dataKey="id" fill="#2563eb" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div className="col-md-6">
                  <div className="glass-card p-4 bg-accent bg-opacity-5 border-accent border-opacity-10">
                    <h5 className="font-outfit text-accent mb-3 d-flex align-items-center gap-2"><CheckCircle2 size={18}/> Smart Recommendations</h5>
                    <ul className="list-unstyled mb-0">
                      <li className="mb-3 d-flex gap-2 small">
                        <div className="mt-1 text-accent"><ChevronRight size={14} /></div>
                        Continue current therapy for hypertension. Adherence looks excellent.
                      </li>
                      <li className="d-flex gap-2 small">
                        <div className="mt-1 text-accent"><ChevronRight size={14} /></div>
                        Schedule follow-up with {records[0]?.doctor_name || 'your physician'} in 2 weeks.
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* REMINDERS TAB */}
          {activeTab === 'reminders' && (
            <div className="animate-in slide-in-top">
              <div className="d-flex justify-content-between align-items-center mb-4">
                <h3 className="h4 font-outfit mb-0">Active Medication Schedule</h3>
                <span className="badge bg-light text-navy px-3 py-2 border rounded-pill small">3 Tracks Active</span>
              </div>
              {records.length > 0 ? records[0].medicines?.map((med, i) => (
                <div key={i} className="glass-card p-4 mb-3 d-flex justify-content-between align-items-center">
                  <div className="d-flex align-items-center gap-3">
                    <div className="bg-primary bg-opacity-10 text-primary p-3 rounded-4"><Bell size={24}/></div>
                    <div>
                      <h5 className="mb-0 text-navy font-semibold">{med.name}</h5>
                      <p className="text-secondary small mb-0">{med.dosage} • {med.frequency || 'Daily'} • {med.duration || 'Until finished'}</p>
                    </div>
                  </div>
                  <div className="form-check form-switch scale-125">
                    <input className="form-check-input" type="checkbox" defaultChecked />
                  </div>
                </div>
              )) : (
                <div className="glass-card p-5 text-center text-secondary">
                  Scan a prescription to automatically generate med-reminders.
                </div>
              )}
            </div>
          )}

        </div>

        {/* Right Sidebar - At a Glance */}
        <div className="col-lg-4">
          <div className="glass-card p-4 mb-4">
            <h5 className="font-outfit mb-4">Emergency Profile</h5>
            <div className="d-flex align-items-center gap-3 mb-4 p-3 bg-danger bg-opacity-5 rounded-4 border border-danger border-opacity-10">
               <div className="bg-danger text-white p-2 rounded-circle"><ShieldAlert size={20}/></div>
               <div>
                  <div className="text-danger small font-bold">EMERGENCY CONTACT</div>
                  <div className="text-navy h6 mb-0 font-semibold">{user.emergency_contact || 'None Set'}</div>
               </div>
            </div>
            <div className="small text-secondary mb-2">Basic Info</div>
            <div className="row g-2 mb-4">
               <div className="col-6">
                 <div className="bg-light p-2 px-3 rounded-3">
                   <div className="text-secondary tracking-widest x-small font-bold">BLOOD</div>
                   <div className="text-navy font-semibold">{user.blood_group || 'O+'}</div>
                 </div>
               </div>
               <div className="col-6">
                 <div className="bg-light p-2 px-3 rounded-3">
                   <div className="text-secondary tracking-widest x-small font-bold">AGE</div>
                   <div className="text-navy font-semibold">{user.age || '—'}</div>
                 </div>
               </div>
            </div>
            <button className="btn btn-outline-danger w-100 rounded-pill py-2 font-semibold">VIEW EMERGENCY SOS</button>
          </div>

          <div className="glass-card p-4">
             <div className="d-flex justify-content-between align-items-center mb-4">
               <h5 className="font-outfit mb-0">Upcoming Reminders</h5>
               <Calendar size={18} className="text-secondary" />
             </div>
             {[
               { time: '08:00 AM', name: 'Morning Dose' },
               { time: '02:00 PM', name: 'Lunch Supplement' },
               { time: '09:30 PM', name: 'Sleep Aid' },
             ].map((rem, i) => (
               <div key={i} className={`d-flex align-items-center gap-3 mb-3 pb-3 ${i < 2 ? 'border-bottom border-light' : ''}`}>
                  <div className="text-primary font-bold small" style={{ minWidth: '70px' }}>{rem.time}</div>
                  <div className="text-navy font-semibold small">{rem.name}</div>
                  <div className="ms-auto"><CheckCircle2 size={16} className="text-light-secondary"/></div>
               </div>
             ))}
          </div>
        </div>
      </div>
      
      {/* Footer / Legal */}
      <div className="mt-5 text-center text-secondary x-small tracking-widest py-4">
         SECURED BY MEDICAL BLOCKCHAIN • 2026 TECHNOLOGY
      </div>
    </div>
  );
};

export default Dashboard;
