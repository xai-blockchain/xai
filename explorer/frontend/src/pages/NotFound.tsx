import { Link } from 'react-router-dom';
import { Home, Search } from 'lucide-react';

export function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="text-8xl font-bold text-xai-primary mb-4">404</div>
      <h1 className="text-2xl font-semibold text-white mb-2">Page Not Found</h1>
      <p className="text-xai-muted mb-8 text-center max-w-md">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <div className="flex items-center gap-4">
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-4 py-2 bg-xai-primary text-black rounded-lg font-medium hover:bg-xai-secondary transition-colors"
        >
          <Home className="h-4 w-4" />
          Go Home
        </Link>
        <Link
          to="/blocks"
          className="inline-flex items-center gap-2 px-4 py-2 bg-xai-card text-white rounded-lg font-medium hover:bg-xai-border transition-colors"
        >
          <Search className="h-4 w-4" />
          Browse Blocks
        </Link>
      </div>
    </div>
  );
}
