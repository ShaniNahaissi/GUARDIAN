import React, { useCallback, useEffect, useState } from 'react';
import { Users, Plus, Pencil, Trash2, ArrowLeft, Settings, Activity } from 'lucide-react';
import { Card } from '../components/atoms/Card';
import { Button } from '../components/atoms/Button';
import { useToast } from '../context/ToastContext';
import {
  createAdminUser,
  deleteAdminUser,
  listAdminUsers,
  updateAdminUser,
  type AdminUserRow,
} from '../services/adminUsersApi';
import type { AppRole } from '../services/authApi';
import { AdminMetricsDashboard } from '../components/molecules/AdminMetricsDashboard';
import { PhoneInput } from '../components/atoms/PhoneInput';

const ROLES: AppRole[] = ['admin', 'operator', 'viewer'];

interface AdminUsersPageProps {
  onBack: () => void;
}

export const AdminUsersPage: React.FC<AdminUsersPageProps> = ({ onBack }) => {
  const { showToast } = useToast();
  const [rows, setRows] = useState<AdminUserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newPrimaryPhone, setNewPrimaryPhone] = useState('');
  const [newAdditionalPhone, setNewAdditionalPhone] = useState('');
  const [newRole, setNewRole] = useState<AppRole>('viewer');
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<AdminUserRow | null>(null);
  const [editFullName, setEditFullName] = useState('');
  const [editPrimaryPhone, setEditPrimaryPhone] = useState('');
  const [editAdditionalPhone, setEditAdditionalPhone] = useState('');
  const [editRole, setEditRole] = useState<AppRole>('viewer');
  const [editPassword, setEditPassword] = useState('');
  const [activeTab, setActiveTab] = useState<'metrics' | 'users'>('metrics');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listAdminUsers();
      setRows(data);
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Failed to load users', 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    void load();
  }, [load]);

  const openEdit = (u: AdminUserRow) => {
    setEditing(u);
    setEditFullName(u.fullName);
    setEditPrimaryPhone(u.primaryPhone || '');
    setEditAdditionalPhone(u.additionalPhone || '');
    setEditRole(u.role);
    setEditPassword('');
  };

  const closeEdit = () => {
    setEditing(null);
    setEditPassword('');
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await createAdminUser({
        username: newUsername.trim(),
        password: newPassword,
        full_name: newFullName.trim(),
        role: newRole,
        primary_phone: newPrimaryPhone.trim(),
        additional_phone: newAdditionalPhone.trim(),
      });
      showToast('User created', 'success');
      setNewUsername('');
      setNewPassword('');
      setNewFullName('');
      setNewPrimaryPhone('');
      setNewAdditionalPhone('');
      setNewRole('viewer');
      await load();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Create failed', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editing) return;
    setSaving(true);
    try {
      const payload: {
        full_name: string;
        role: AppRole;
        password?: string;
        primary_phone: string;
        additional_phone: string;
      } = {
        full_name: editFullName.trim(),
        role: editRole,
        primary_phone: editPrimaryPhone.trim(),
        additional_phone: editAdditionalPhone.trim(),
      };
      if (editPassword.trim()) payload.password = editPassword.trim();
      await updateAdminUser(editing.id, payload);
      showToast('User updated', 'success');
      closeEdit();
      await load();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Update failed', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (u: AdminUserRow) => {
    if (!window.confirm(`Delete user “${u.username}”? This cannot be undone.`)) return;
    try {
      await deleteAdminUser(u.id);
      showToast('User deleted', 'success');
      if (editing?.id === u.id) closeEdit();
      await load();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Delete failed', 'error');
    }
  };

  const formatCreated = (iso: string | null) => {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <button
            type="button"
            onClick={onBack}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors shrink-0"
            aria-label="Back to dashboard"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>
          <div>
            <h2 className="text-xl sm:text-2xl font-bold flex items-center gap-2">
              <Settings className="w-7 h-7 text-guardian-accent shrink-0" />
              Admin Control Center
            </h2>
            <p className="text-guardian-muted text-sm mt-1">
              Configure system metrics logging, database persistent performance logs, and manage user accounts.
            </p>
          </div>
        </div>
        {activeTab === 'users' && (
          <Button variant="secondary" type="button" onClick={() => void load()} disabled={loading}>
            Refresh
          </Button>
        )}
      </div>

      {/* Sub-navigation Tabs */}
      <div className="flex border-b border-gray-800 gap-6 text-sm">
        <button
          onClick={() => setActiveTab('metrics')}
          className={`pb-3 font-semibold transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === 'metrics'
              ? 'border-guardian-accent text-white'
              : 'border-transparent text-guardian-muted hover:text-white'
          }`}
        >
          <Activity className="w-4 h-4" />
          Metrics Dashboard
        </button>
        <button
          onClick={() => setActiveTab('users')}
          className={`pb-3 font-semibold transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === 'users'
              ? 'border-guardian-accent text-white'
              : 'border-transparent text-guardian-muted hover:text-white'
          }`}
        >
          <Users className="w-4 h-4" />
          User Accounts
        </button>
      </div>

      {activeTab === 'metrics' && <AdminMetricsDashboard />}

      {activeTab === 'users' && (
        <>
          <Card className="p-4 sm:p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Plus className="w-5 h-5 text-guardian-accent" />
              Add user
            </h3>
            <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
              <div>
                <label className="block text-xs text-guardian-muted mb-1">Username</label>
                <input
                  required
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-guardian-accent"
                />
              </div>
              <div>
                <label className="block text-xs text-guardian-muted mb-1">Password</label>
                <input
                  required
                  type="password"
                  minLength={4}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-guardian-accent"
                />
              </div>
              <div>
                <label className="block text-xs text-guardian-muted mb-1">Full name</label>
                <input
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-guardian-accent"
                  placeholder="Optional"
                />
              </div>
              <PhoneInput
                label="Primary Phone"
                value={newPrimaryPhone}
                onChange={setNewPrimaryPhone}
                placeholder="050-123-4567"
              />
              <PhoneInput
                label="Additional Phone"
                value={newAdditionalPhone}
                onChange={setNewAdditionalPhone}
                placeholder="052-987-6543"
              />
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="block text-xs text-guardian-muted mb-1">Role</label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value as AppRole)}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-guardian-accent"
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
                <Button type="submit" className="shrink-0 self-end" disabled={saving}>
                  Add
                </Button>
              </div>
            </form>
          </Card>

          <Card className="p-0 overflow-hidden border border-gray-800">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 bg-gray-900/50 text-left text-guardian-muted">
                    <th className="px-4 py-3 font-medium">Username</th>
                    <th className="px-4 py-3 font-medium">Name</th>
                    <th className="px-4 py-3 font-medium">Primary Phone</th>
                    <th className="px-4 py-3 font-medium">Role</th>
                    <th className="px-4 py-3 font-medium hidden md:table-cell">Created</th>
                    <th className="px-4 py-3 font-medium w-32 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {loading && (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-guardian-muted">
                        Loading…
                      </td>
                    </tr>
                  )}
                  {!loading &&
                    rows.map((u) => (
                      <tr key={u.id} className="border-b border-gray-800/80 hover:bg-gray-900/30">
                        <td className="px-4 py-3 font-mono text-white">{u.username}</td>
                        <td className="px-4 py-3">{u.fullName}</td>
                        <td className="px-4 py-3 font-mono text-xs text-guardian-accent">{u.primaryPhone || '—'}</td>
                        <td className="px-4 py-3 capitalize">{u.role}</td>
                        <td className="px-4 py-3 text-guardian-muted hidden md:table-cell whitespace-nowrap">
                          {formatCreated(u.createdAt)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            type="button"
                            onClick={() => openEdit(u)}
                            className="p-2 rounded-lg text-guardian-accent hover:bg-gray-800 inline-flex"
                            aria-label={`Edit ${u.username}`}
                          >
                            <Pencil className="w-4 h-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => void handleDelete(u)}
                            className="p-2 rounded-lg text-guardian-danger hover:bg-red-500/10 inline-flex ml-1"
                            aria-label={`Delete ${u.username}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  {!loading && rows.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-guardian-muted">
                        No users found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          {editing && (
            <Card className="p-4 sm:p-6 border border-guardian-accent/30">
              <h3 className="text-lg font-semibold mb-4">Edit {editing.username}</h3>
              <form onSubmit={handleSaveEdit} className="space-y-4 max-w-md">
                <div>
                  <label className="block text-xs text-guardian-muted mb-1">Full name</label>
                  <input
                    value={editFullName}
                    onChange={(e) => setEditFullName(e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-guardian-accent"
                  />
                </div>
                <PhoneInput
                  label="Primary Phone Number"
                  value={editPrimaryPhone}
                  onChange={setEditPrimaryPhone}
                  placeholder="050-123-4567"
                />
                <PhoneInput
                  label="Additional Alert Phone Number"
                  value={editAdditionalPhone}
                  onChange={setEditAdditionalPhone}
                  placeholder="052-987-6543"
                />
                <div>
                  <label className="block text-xs text-guardian-muted mb-1">Role</label>
                  <select
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value as AppRole)}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-guardian-accent"
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-guardian-muted mb-1">New password (optional)</label>
                  <input
                    type="password"
                    minLength={4}
                    value={editPassword}
                    onChange={(e) => setEditPassword(e.target.value)}
                    placeholder="Leave blank to keep current"
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-guardian-accent"
                  />
                </div>
                <div className="flex gap-3">
                  <Button type="submit" disabled={saving}>
                    Save
                  </Button>
                  <Button type="button" variant="secondary" onClick={closeEdit}>
                    Cancel
                  </Button>
                </div>
              </form>
            </Card>
          )}
        </>
      )}
    </div>
  );
};
