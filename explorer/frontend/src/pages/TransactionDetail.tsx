import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowRightLeft, ChevronLeft, ArrowRight, Cpu } from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { Badge, getStatusVariant } from '../components/Badge';
import { AddressLink, HashLink } from '../components/HashLink';
import { CopyButton } from '../components/CopyButton';
import { Loading } from '../components/Loading';
import { getTransaction } from '../api/client';
import { formatNumber, formatDate, formatTimeAgo, formatXAI } from '../utils/format';

export function TransactionDetail() {
  const { txid } = useParams<{ txid: string }>();

  const { data: tx, isLoading, error } = useQuery({
    queryKey: ['transaction', txid],
    queryFn: () => getTransaction(txid!),
    enabled: !!txid,
  });

  if (isLoading) {
    return <Loading message="Loading transaction..." />;
  }

  if (error || !tx) {
    return (
      <div className="text-center py-12">
        <ArrowRightLeft className="h-16 w-16 text-xai-muted mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-white mb-2">Transaction Not Found</h2>
        <p className="text-xai-muted mb-6">
          The transaction you're looking for doesn't exist or is still pending.
        </p>
        <Link
          to="/transactions"
          className="inline-flex items-center gap-2 px-4 py-2 bg-xai-primary text-black rounded-lg font-medium hover:bg-xai-secondary transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Transactions
        </Link>
      </div>
    );
  }

  const details = [
    {
      label: 'Transaction ID',
      value: (
        <span className="flex items-center gap-2">
          <span className="font-mono text-sm break-all">{tx.txid}</span>
          <CopyButton text={tx.txid} />
        </span>
      ),
    },
    {
      label: 'Status',
      value: (
        <Badge variant={getStatusVariant(tx.status)}>
          {tx.status} {tx.confirmations > 0 && `(${tx.confirmations} confirmations)`}
        </Badge>
      ),
    },
    {
      label: 'Block',
      value: (
        <Link to={`/block/${tx.blockHeight}`} className="text-xai-primary hover:underline">
          {formatNumber(tx.blockHeight)}
        </Link>
      ),
    },
    { label: 'Timestamp', value: `${formatDate(tx.timestamp)} (${formatTimeAgo(tx.timestamp)})` },
    {
      label: 'Type',
      value: (
        <Badge variant={tx.type === 'ai_task' ? 'primary' : 'default'}>
          {tx.type === 'ai_task' && <Cpu className="h-3 w-3 mr-1" />}
          {tx.type.replace('_', ' ').toUpperCase()}
        </Badge>
      ),
    },
    {
      label: 'From',
      value: <AddressLink address={tx.from} truncate={false} showCopy />,
    },
    {
      label: 'To',
      value: <AddressLink address={tx.to} truncate={false} showCopy />,
    },
    { label: 'Amount', value: <span className="text-xl font-semibold text-xai-primary">{formatXAI(tx.amount)}</span> },
    { label: 'Fee', value: formatXAI(tx.fee) },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-xai-primary/10">
          <ArrowRightLeft className="h-5 w-5 text-xai-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Transaction Details</h1>
          <p className="text-sm text-xai-muted font-mono">
            {tx.txid.slice(0, 16)}...{tx.txid.slice(-8)}
          </p>
        </div>
      </div>

      {/* Transaction Overview */}
      <Card>
        <CardHeader title="Overview" />
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

      {/* Inputs & Outputs */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Inputs */}
        <Card>
          <CardHeader title={`Inputs (${tx.inputs?.length || 1})`} />
          <div className="space-y-3">
            {tx.inputs && tx.inputs.length > 0 ? (
              tx.inputs.map((input, index) => (
                <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-xai-dark">
                  <div>
                    <AddressLink address={input.address} />
                    <p className="text-xs text-xai-muted mt-1">
                      vout: {input.vout}
                    </p>
                  </div>
                  <span className="text-white font-medium">{formatXAI(input.amount)}</span>
                </div>
              ))
            ) : (
              <div className="flex items-center justify-between p-3 rounded-lg bg-xai-dark">
                <AddressLink address={tx.from} />
                <span className="text-white font-medium">{formatXAI(tx.amount)}</span>
              </div>
            )}
          </div>
        </Card>

        {/* Outputs */}
        <Card>
          <CardHeader title={`Outputs (${tx.outputs?.length || 1})`} />
          <div className="space-y-3">
            {tx.outputs && tx.outputs.length > 0 ? (
              tx.outputs.map((output, index) => (
                <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-xai-dark">
                  <div>
                    <AddressLink address={output.address} />
                    <p className="text-xs text-xai-muted mt-1">
                      index: {output.index}
                    </p>
                  </div>
                  <span className="text-white font-medium">{formatXAI(output.amount)}</span>
                </div>
              ))
            ) : (
              <div className="flex items-center justify-between p-3 rounded-lg bg-xai-dark">
                <AddressLink address={tx.to} />
                <span className="text-white font-medium">{formatXAI(tx.amount)}</span>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* AI Task Details (if applicable) */}
      {tx.aiTask && (
        <Card>
          <CardHeader
            title="AI Task Details"
            subtitle="This transaction is associated with an AI compute task"
          />
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="p-3 rounded-lg bg-xai-dark">
              <p className="text-xai-muted text-sm">Task ID</p>
              <Link
                to={`/ai/${tx.aiTask.taskId}`}
                className="text-xai-primary hover:underline font-mono"
              >
                {tx.aiTask.taskId}
              </Link>
            </div>
            <div className="p-3 rounded-lg bg-xai-dark">
              <p className="text-xai-muted text-sm">AI Model</p>
              <p className="text-white">{tx.aiTask.aiModel}</p>
            </div>
            <div className="p-3 rounded-lg bg-xai-dark">
              <p className="text-xai-muted text-sm">Task Type</p>
              <p className="text-white capitalize">{tx.aiTask.taskType.replace('_', ' ')}</p>
            </div>
            <div className="p-3 rounded-lg bg-xai-dark">
              <p className="text-xai-muted text-sm">Status</p>
              <Badge variant={getStatusVariant(tx.aiTask.status)}>
                {tx.aiTask.status}
              </Badge>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
