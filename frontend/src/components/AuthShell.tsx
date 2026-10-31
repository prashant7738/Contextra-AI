import { useState, type InputHTMLAttributes, type ReactNode } from 'react';
import './AuthPages.css';

const PERKS = [
  'Chat with your PDFs and get cited answers',
  '80/20 summaries of a whole semester',
  'Flashcards generated in seconds',
];

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="auth-container">
      <aside className="auth-aside" aria-hidden="true">
        <a href="/" className="auth-brand">
          Contextra<span>AI</span>
        </a>
        <h2>Your documents, supercharged.</h2>
        <ul>
          {PERKS.map((perk) => (
            <li key={perk}>{perk}</li>
          ))}
        </ul>
      </aside>
      <div className="auth-main">
        <a href="/" className="auth-brand auth-brand-mobile">
          Contextra<span>AI</span>
        </a>
        {children}
      </div>
    </div>
  );
}

export function PasswordInput(props: InputHTMLAttributes<HTMLInputElement>) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="password-field">
      <input {...props} type={visible ? 'text' : 'password'} />
      <button
        type="button"
        className="password-toggle"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? 'Hide password' : 'Show password'}
        aria-pressed={visible}
        disabled={props.disabled}
      >
        {visible ? 'Hide' : 'Show'}
      </button>
    </div>
  );
}
