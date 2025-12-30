import { Link } from 'react-router-dom';
import { truncateHash } from '../utils/format';
import { CopyButton } from './CopyButton';

interface HashLinkProps {
  hash: string;
  to: string;
  truncate?: boolean;
  showCopy?: boolean;
  className?: string;
}

export function HashLink({ hash, to, truncate = true, showCopy = false, className }: HashLinkProps) {
  const displayHash = truncate ? truncateHash(hash) : hash;

  return (
    <span className="inline-flex items-center gap-1">
      <Link
        to={to}
        className={`font-mono text-xai-primary hover:underline ${className || ''}`}
        title={hash}
      >
        {displayHash}
      </Link>
      {showCopy && <CopyButton text={hash} />}
    </span>
  );
}

interface AddressLinkProps {
  address: string;
  truncate?: boolean;
  showCopy?: boolean;
  className?: string;
}

export function AddressLink({ address, truncate = true, showCopy = false, className }: AddressLinkProps) {
  const displayAddress = truncate ? truncateHash(address, 6, 6) : address;

  return (
    <span className="inline-flex items-center gap-1">
      <Link
        to={`/address/${address}`}
        className={`font-mono text-xai-primary hover:underline ${className || ''}`}
        title={address}
      >
        {displayAddress}
      </Link>
      {showCopy && <CopyButton text={address} />}
    </span>
  );
}
