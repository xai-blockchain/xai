import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Blocks, ChevronLeft, ChevronRight, ArrowRightLeft } from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../components/Table';
import { Badge } from '../components/Badge';
import { HashLink, AddressLink } from '../components/HashLink';
import { CopyButton } from '../components/CopyButton';
import { Loading } from '../components/Loading';
import { getBlock } from '../api/client';
import { formatNumber, formatDate, formatTimeAgo, formatBytes } from '../utils/format';

export function BlockDetail() {
  const { blockId } = useParams<{ blockId: string }>();

  const { data: block, isLoading, error } = useQuery({
    queryKey: ['block', blockId],
    queryFn: () => getBlock(blockId!),
    enabled: !!blockId,
  });

  if (isLoading) {
    return <Loading message="Loading block..." />;
  }

  if (error || !block) {
    return (
      <div className="text-center py-12">
        <Blocks className="h-16 w-16 text-xai-muted mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-white mb-2">Block Not Found</h2>
        <p className="text-xai-muted mb-6">
          The block you're looking for doesn't exist or hasn't been mined yet.
        </p>
        <Link
          to="/blocks"
          className="inline-flex items-center gap-2 px-4 py-2 bg-xai-primary text-black rounded-lg font-medium hover:bg-xai-secondary transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Blocks
        </Link>
      </div>
    );
  }

  const details = [
    { label: 'Block Height', value: formatNumber(block.height) },
    { label: 'Timestamp', value: `${formatDate(block.timestamp)} (${formatTimeAgo(block.timestamp)})` },
    {
      label: 'Block Hash',
      value: (
        <span className="flex items-center gap-2">
          <span className="font-mono text-sm break-all">{block.hash}</span>
          <CopyButton text={block.hash} />
        </span>
      ),
    },
    {
      label: 'Previous Hash',
      value: block.previousHash ? (
        <HashLink hash={block.previousHash} to={`/block/${block.previousHash}`} truncate={false} showCopy />
      ) : (
        <span className="text-xai-muted">Genesis Block</span>
      ),
    },
    {
      label: 'Miner',
      value: block.miner ? (
        <AddressLink address={block.miner} truncate={false} showCopy />
      ) : (
        <span className="text-xai-muted">Unknown</span>
      ),
    },
    { label: 'Difficulty', value: formatNumber(block.difficulty || 0) },
    { label: 'Nonce', value: formatNumber(block.nonce || 0) },
    { label: 'Size', value: formatBytes(block.size || 0) },
    {
      label: 'Merkle Root',
      value: (
        <span className="flex items-center gap-2">
          <span className="font-mono text-sm break-all">{block.merkleRoot || 'N/A'}</span>
          {block.merkleRoot && <CopyButton text={block.merkleRoot} />}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-primary/10">
            <Blocks className="h-5 w-5 text-xai-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">
              Block #{formatNumber(block.height)}
            </h1>
            <p className="text-sm text-xai-muted">
              {formatTimeAgo(block.timestamp)}
            </p>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex items-center gap-2">
          <Link
            to={`/block/${block.height - 1}`}
            className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition-colors ${
              block.height > 0
                ? 'bg-xai-card text-white hover:bg-xai-border'
                : 'bg-xai-card/50 text-xai-muted cursor-not-allowed'
            }`}
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Link>
          <Link
            to={`/block/${block.height + 1}`}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-xai-card text-white hover:bg-xai-border transition-colors"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
      </div>

      {/* Block Details */}
      <Card>
        <CardHeader title="Block Details" />
        <div className="space-y-4">
          {details.map((item, index) => (
            <div
              key={item.label}
              className={`flex flex-col sm:flex-row sm:items-start gap-2 py-3 ${
                index < details.length - 1 ? 'border-b border-xai-border' : ''
              }`}
            >
              <span className="text-xai-muted sm:w-40 shrink-0">{item.label}</span>
              <span className="text-white flex-1">{item.value}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Transactions */}
      <Card padding="none">
        <div className="p-6 pb-0">
          <CardHeader
            title={`Transactions (${block.transactions?.length || 0})`}
            subtitle="All transactions included in this block"
          />
        </div>
        {block.transactions && block.transactions.length > 0 ? (
          <Table>
            <TableHeader>
              <TableHead>Transaction ID</TableHead>
              <TableHead align="right">Index</TableHead>
            </TableHeader>
            <TableBody>
              {block.transactions.map((tx, index) => {
                const txid = typeof tx === 'string' ? tx : tx.txid;
                return (
                  <TableRow key={txid}>
                    <TableCell>
                      <HashLink hash={txid} to={`/tx/${txid}`} showCopy />
                    </TableCell>
                    <TableCell align="right" className="text-xai-muted">
                      {index}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        ) : (
          <div className="p-8 text-center">
            <ArrowRightLeft className="h-12 w-12 text-xai-muted mx-auto mb-3" />
            <p className="text-xai-muted">No transactions in this block</p>
          </div>
        )}
      </Card>
    </div>
  );
}
