import React, { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  Radar,
  PlusCircle,
  Clock,
  FileCheck2,
  Scale,
  LayoutDashboard,
  Sliders,
  ChevronDown,
  Lock,
  Users,
  X,
} from 'lucide-react';
import { isMockMode, setMockMode } from '../../services/api';

interface SidebarProps {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ mobileOpen, onMobileClose }) => {
  const location = useLocation();
  const [mockActive, setMockActive] = useState(isMockMode());
  const [workspaceMenuOpen, setWorkspaceMenuOpen] = useState(false);
  const [activeScope, setActiveScope] = useState<'PERSONAL' | 'WORKSPACE'>('PERSONAL');

  useEffect(() => {
    const handleMockChange = (e: Event) => {
      const custom = e as CustomEvent<boolean>;
      setMockActive(custom.detail);
    };
    window.addEventListener('changeradar:mockmode_changed', handleMockChange);
    return () => {
      window.removeEventListener('changeradar:mockmode_changed', handleMockChange);
    };
  }, []);

  const toggleMock = () => {
    const next = !mockActive;
    setMockMode(next);
    setMockActive(next);
  };

  const navItems = [
    { name: 'Overview', to: '/', icon: LayoutDashboard },
    { name: 'New Research', to: '/new', icon: PlusCircle },
    { name: 'Research History', to: '/history', icon: Clock },
    { name: 'Evidence Ledger', to: '/evidence', icon: FileCheck2 },
    { name: 'Stress Test', to: '/stress-test', icon: Scale },
  ];

  const sidebarContent = (
    <div className="flex flex-col h-full bg-bg-secondary border-r border-border w-64 select-none">
      {/* Brand Header */}
      <div className="flex items-center justify-between px-5 h-16 border-b border-border">
        <NavLink to="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-bg-elevated border border-border flex items-center justify-center text-accent group-hover:border-accent transition-colors duration-200">
            <Radar className="w-5 h-5 text-accent" />
          </div>
          <div className="flex flex-col">
            <span className="font-heading font-bold text-base tracking-tight text-text-primary">
              Change<span className="text-accent">Radar</span>
            </span>
            <span className="text-[10px] font-mono text-text-muted tracking-widest uppercase">
              Evidence Intel
            </span>
          </div>
        </NavLink>
        {mobileOpen && (
          <button
            type="button"
            onClick={onMobileClose}
            className="md:hidden text-text-muted hover:text-text-primary p-1"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Scope Selector (Personal vs Workspace) */}
      <div className="px-4 py-3 border-b border-border/60">
        <div className="relative">
          <button
            type="button"
            onClick={() => setWorkspaceMenuOpen(!workspaceMenuOpen)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-bg-elevated border border-border hover:border-border-active text-left transition-colors text-xs"
          >
            <div className="flex items-center gap-2 truncate">
              {activeScope === 'PERSONAL' ? (
                <Lock className="w-3.5 h-3.5 text-accent" />
              ) : (
                <Users className="w-3.5 h-3.5 text-status-info" />
              )}
              <span className="font-medium text-text-primary truncate">
                {activeScope === 'PERSONAL' ? 'Personal Scope' : 'Workspace Scope'}
              </span>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-text-muted shrink-0" />
          </button>

          {workspaceMenuOpen && (
            <div className="absolute top-full left-0 right-0 mt-1.5 bg-bg-elevated border border-border rounded-lg shadow-xl py-1 z-50 text-xs">
              <button
                type="button"
                onClick={() => {
                  setActiveScope('PERSONAL');
                  setWorkspaceMenuOpen(false);
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-bg-secondary ${
                  activeScope === 'PERSONAL' ? 'text-accent font-medium' : 'text-text-secondary'
                }`}
              >
                <Lock className="w-3.5 h-3.5" />
                <div className="flex flex-col">
                  <span>Personal Research</span>
                  <span className="text-[10px] text-text-muted">Private to your account</span>
                </div>
              </button>
              <button
                type="button"
                onClick={() => {
                  setActiveScope('WORKSPACE');
                  setWorkspaceMenuOpen(false);
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-bg-secondary ${
                  activeScope === 'WORKSPACE' ? 'text-status-info font-medium' : 'text-text-secondary'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <div className="flex flex-col">
                  <span>Workspace Scope</span>
                  <span className="text-[10px] text-text-muted">Shared with team members</span>
                </div>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Primary Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-mono uppercase tracking-wider text-text-muted">
          Intelligence
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.to === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.to);

          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onMobileClose}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 ${
                isActive
                  ? 'bg-accent/10 text-accent font-semibold border-l-2 border-accent pl-2.5'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
              }`}
            >
              <Icon
                className={`w-4 h-4 ${
                  isActive ? 'text-accent' : 'text-text-muted group-hover:text-text-primary'
                }`}
              />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Environment / Mock Mode Toggle Affordance */}
      <div className="px-4 py-3 border-t border-border/60 bg-bg-primary/50">
        <div className="flex items-center justify-between text-xs mb-2">
          <span className="text-text-muted flex items-center gap-1.5 font-mono">
            <Sliders className="w-3.5 h-3.5 text-accent" />
            <span>DATA SOURCE</span>
          </span>
          <span
            className={`font-mono text-[10px] uppercase px-1.5 py-0.5 rounded ${
              mockActive
                ? 'bg-status-warning/15 text-status-warning border border-status-warning/30'
                : 'bg-status-success/15 text-status-success border border-status-success/30'
            }`}
          >
            {mockActive ? 'FIXTURES' : 'LIVE API'}
          </span>
        </div>
        <button
          type="button"
          onClick={toggleMock}
          className="w-full text-left text-xs text-text-secondary hover:text-text-primary p-1.5 rounded bg-bg-elevated border border-border/80 flex items-center justify-between transition-colors"
          title="Switch between mock demonstration fixtures and live backend API"
        >
          <span className="truncate">
            {mockActive ? 'Switch to Live API' : 'Switch to Demo Fixtures'}
          </span>
          <span className="text-[10px] font-mono text-accent">Toggle</span>
        </button>
      </div>

      {/* User / Workspace Footer */}
      <div className="p-4 border-t border-border flex items-center gap-3 bg-bg-secondary">
        <div className="w-8 h-8 rounded-full bg-accent/20 border border-accent/40 flex items-center justify-center text-accent font-heading font-semibold text-xs">
          K
        </div>
        <div className="flex flex-col truncate">
          <span className="text-xs font-medium text-text-primary truncate">
            Koushik (Frontend)
          </span>
          <span className="text-[10px] text-text-muted truncate font-mono">
            team@changeradar.internal
          </span>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Fixed Sidebar */}
      <aside className="hidden md:block fixed inset-y-0 left-0 z-30">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden flex">
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-sm"
            onClick={onMobileClose}
            aria-hidden="true"
          />
          <div className="relative z-50 flex-1 max-w-xs w-full bg-bg-secondary">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};

