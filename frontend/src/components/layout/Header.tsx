import React from 'react';
import { Menu, Plus, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { isMockMode } from '../../services/api';

interface HeaderProps {
  onOpenMobileMenu: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenMobileMenu }) => {
  const navigate = useNavigate();
  const mockEnabled = isMockMode();

  return (
    <header className="sticky top-0 z-20 h-16 bg-bg-primary/90 backdrop-blur border-b border-border px-4 md:px-8 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobileMenu}
          className="md:hidden text-text-secondary hover:text-text-primary p-2 rounded-lg bg-bg-elevated border border-border"
          aria-label="Open mobile navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="hidden sm:flex items-center gap-2 text-xs font-mono text-text-muted bg-bg-elevated/70 px-2.5 py-1 rounded-md border border-border/60">
          <ShieldCheck className="w-3.5 h-3.5 text-accent" />
          <span>EVIDENCE-GROUNDED • SYNDICATION-AWARE</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {mockEnabled && (
          <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono bg-status-warning/15 text-status-warning border border-status-warning/30">
            <span className="w-1.5 h-1.5 rounded-full bg-status-warning" />
            <span>MOCK EVALUATION MODE</span>
          </span>
        )}

        <button
          type="button"
          onClick={() => navigate('/new')}
          className="radar-button-primary text-xs py-2 px-3.5"
        >
          <Plus className="w-4 h-4" />
          <span className="font-medium">New Research</span>
        </button>
      </div>
    </header>
  );
};

