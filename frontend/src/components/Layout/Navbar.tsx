import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import React from 'react';
export default function Navbar() {
  const { user, tenant, logout } = useAuthStore();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <header className="bg-white border-b border-gray-200 h-14 flex items-center justify-between px-6 flex-shrink-0">
      <div className="flex items-center gap-3">
        <Link to="/" className="text-xl font-bold text-blue-600">
          🏗 To.
        </Link>
        {tenant && (
          <span className="text-sm text-gray-500 border-l border-gray-200 pl-3">{tenant.name}</span>
        )}
      </div>
      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <div className="hidden sm:block">
              <p className="text-sm font-medium text-gray-700">{user.name}</p>
              <p className="text-xs text-gray-400 capitalize">{user.role}</p>
            </div>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-red-500 transition-colors"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
