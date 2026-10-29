import Icon from './Icon.jsx';

/** Dismissible error banner with the server's (friendly) message and a "Try again" button. */
export default function ErrorBanner({ error, onRetry, onDismiss }) {
  return (
    <div className="banner banner--error" role="alert">
      <Icon name="warn" size={20} />
      <p className="banner__text">{error.message}</p>
      <div className="banner__actions">
        {onRetry && (
          <button type="button" className="btn btn--secondary btn--small" onClick={onRetry}>
            Try again
          </button>
        )}
        <button type="button" className="btn btn--ghost btn--small" onClick={onDismiss} aria-label="Dismiss error">
          <Icon name="cross" size={16} />
        </button>
      </div>
    </div>
  );
}
