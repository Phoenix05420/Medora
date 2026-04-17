import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ShieldAlert, Users, Trash2, Hospital } from 'lucide-react';

const API_BASE = "http://localhost:8000";

const AdminDashboard = ({ user }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const res = await axios.get(`${API_BASE}/admin/users`, {
        headers: { Authorization: `Bearer ${user.access_token}` }
      });
      setUsers(res.data);
    } catch (err) {
      console.error("Failed to fetch users");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if(!window.confirm("Are you sure you want to permanently delete this user?")) return;
    try {
      await axios.delete(`${API_BASE}/admin/users/${id}`, {
        headers: { Authorization: `Bearer ${user.access_token}` }
      });
      fetchUsers();
    } catch (err) {
      alert("Error deleting user: " + (err.response?.data?.detail || err.message));
    }
  };

  if (loading) return <div className="text-center mt-5"><div className="spinner-border text-primary"/></div>;

  return (
    <div className="container py-5">
      <div className="d-flex justify-content-between align-items-center mb-5">
        <div>
          <h1 className="display-6 font-outfit text-navy d-flex align-items-center gap-3">
            <ShieldAlert size={36} className="text-danger" /> System Overview
          </h1>
          <p className="text-secondary">Ecosystem Control Panel</p>
        </div>
      </div>

      <div className="glass-card p-4">
        <h4 className="h5 mb-4 text-navy">Registered Entities</h4>
        <div className="table-responsive">
          <table className="table align-middle">
            <thead>
              <tr className="text-uppercase x-small text-secondary">
                <th>Entity / Email</th>
                <th>Role</th>
                <th>Joined</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td>
                    <div className="d-flex align-items-center gap-3">
                      <div className={`p-2 rounded bg-opacity-10 ${u.role === 'hospital' ? 'bg-success text-success' : (u.role === 'admin' ? 'bg-danger text-danger' : 'bg-primary text-primary')}`}>
                        {u.role === 'hospital' ? <Hospital size={16}/> : <Users size={16}/>}
                      </div>
                      <div>
                        <div className="font-bold">{u.name}</div>
                        <div className="x-small text-muted">{u.email}</div>
                      </div>
                    </div>
                  </td>
                  <td><span className="badge bg-secondary">{u.role}</span></td>
                  <td className="small">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td>
                    {u.role !== 'admin' && (
                      <button onClick={() => handleDelete(u.id)} className="btn btn-sm btn-outline-danger border-0">
                        <Trash2 size={16} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
