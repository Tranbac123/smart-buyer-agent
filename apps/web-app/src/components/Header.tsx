import Image from 'next/image';
import Link from 'next/link';

interface HeaderProps {
  onToggleSidebar: () => void;
}

export default function Header({ onToggleSidebar }: HeaderProps) {
  return (
    <header className="app-header">
      <div className="header-left">
        <button onClick={onToggleSidebar} className="sidebar-toggle">
          ☰
        </button>
        <Link href="/" className="logo-link">
          <Image src="/logo.svg" alt="QuantumX AI" width={32} height={32} />
          <span className="app-title">QuantumX AI</span>
        </Link>
      </div>
      <div className="header-right">
        <Link href="/admin" className="admin-link">
          Settings
        </Link>
      </div>
    </header>
  );
}

