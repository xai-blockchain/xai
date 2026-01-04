import { useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Blocks, ArrowRightLeft, Users, Clock, Cpu, Zap, TrendingUp, Activity, Download, Droplet, BarChart2, FileCode, Radio } from 'lucide-react';
import { Card, CardHeader } from '../components/Card';
import { StatCard } from '../components/StatCard';
import { Table, TableHeader, TableHead, TableCell } from '../components/Table';
import { Badge, getStatusVariant } from '../components/Badge';
import { HashLink } from '../components/HashLink';
import { Loading } from '../components/Loading';
import { getBlocks, getNetworkStats, getAITasks, getAIStats } from '../api/client';
import { formatNumber, formatTimeAgo, formatXAI } from '../utils/format';
import { useWebSocket, getStatusColor, getStatusText } from '../hooks/useWebSocket';

// Connection status indicator component
function ConnectionStatus({ status }: { status: 'connecting' | 'connected' | 'disconnected' | 'error' }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`relative flex h-3 w-3`}>
        {status === 'connected' && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
        )}
        <span className={`relative inline-flex rounded-full h-3 w-3 ${getStatusColor(status)}`} />
      </span>
      <span className={`text-sm font-medium ${
        status === 'connected' ? 'text-green-400' :
        status === 'connecting' ? 'text-yellow-400' :
        status === 'error' ? 'text-red-400' :
        'text-gray-400'
      }`}>
        {getStatusText(status)}
      </span>
    </div>
  );
}

// Animated row for new items
function AnimatedTableRow({ children, isNew }: { children: React.ReactNode; isNew: boolean }) {
  return (
    <tr className={`border-b border-xai-border transition-all duration-500 ${
      isNew ? 'bg-xai-primary/10 animate-pulse' : ''
    }`}>
      {children}
    </tr>
  );
}

export function Home() {
  const queryClient = useQueryClient();

  // WebSocket connection
  const {
    status: wsStatus,
    latestBlock,
    latestAITask,
    recentBlocks: wsBlocks,
    recentAITasks: wsAITasks,
  } = useWebSocket({
    onBlock: () => {
      // Invalidate queries when new data arrives
      queryClient.invalidateQueries({ queryKey: ['blocks'] });
      queryClient.invalidateQueries({ queryKey: ['networkStats'] });
    },
    onAITask: () => {
      queryClient.invalidateQueries({ queryKey: ['aiTasks'] });
      queryClient.invalidateQueries({ queryKey: ['aiStats'] });
    },
  });

  const { data: blocksData, isLoading: blocksLoading } = useQuery({
    queryKey: ['blocks', 1, 5],
    queryFn: () => getBlocks(1, 5),
    refetchInterval: wsStatus === 'connected' ? 30000 : 10000, // Slower polling when WS connected
  });

  const { data: networkStats, isLoading: statsLoading } = useQuery({
    queryKey: ['networkStats'],
    queryFn: getNetworkStats,
    refetchInterval: 30000,
  });

  const { data: aiTasksData, isLoading: aiTasksLoading } = useQuery({
    queryKey: ['aiTasks', 1, 5],
    queryFn: () => getAITasks({ page: 1, limit: 5 }),
    refetchInterval: wsStatus === 'connected' ? 30000 : 15000,
  });

  const { data: aiStats } = useQuery({
    queryKey: ['aiStats'],
    queryFn: getAIStats,
    refetchInterval: 30000,
  });

  // Merge WS blocks with API blocks, preferring WS for recent ones
  const displayBlocks = useMemo(() => {
    if (wsBlocks.length > 0 && blocksData?.blocks) {
      const wsBlockHashes = new Set(wsBlocks.map(b => b.hash));
      const apiBlocks = blocksData.blocks.filter(b => !wsBlockHashes.has(b.hash));
      return [...wsBlocks, ...apiBlocks].slice(0, 5);
    }
    return blocksData?.blocks || [];
  }, [wsBlocks, blocksData?.blocks]);

  // Merge WS AI tasks with API tasks
  const displayAITasks = useMemo(() => {
    if (wsAITasks.length > 0 && aiTasksData?.tasks) {
      const wsTaskIds = new Set(wsAITasks.map(t => t.taskId));
      const apiTasks = aiTasksData.tasks.filter(t => !wsTaskIds.has(t.taskId));
      return [...wsAITasks, ...apiTasks].slice(0, 5);
    }
    return aiTasksData?.tasks || [];
  }, [wsAITasks, aiTasksData?.tasks]);

  // Track which items are "new" from WebSocket
  const newBlockHashes = useMemo(() => new Set(wsBlocks.slice(0, 2).map(b => b.hash)), [wsBlocks]);
  const newTaskIds = useMemo(() => new Set(wsAITasks.slice(0, 2).map(t => t.taskId)), [wsAITasks]);

  return (
    <div className="space-y-8">
      {/* Hero Section with Connection Status */}
      <div className="text-center py-8">
        <div className="flex justify-center mb-4">
          <ConnectionStatus status={wsStatus} />
        </div>
        <h1 className="text-4xl font-bold text-white mb-4">
          XAI Blockchain Explorer
        </h1>
        <p className="text-xai-muted text-lg max-w-2xl mx-auto">
          Explore blocks, transactions, and AI compute tasks on the XAI network
        </p>
      </div>

      {/* Network Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Blocks"
          value={statsLoading ? '...' : formatNumber(networkStats?.blockchain.totalBlocks || 0)}
          icon={Blocks}
        />
        <StatCard
          label="Total Transactions"
          value={statsLoading ? '...' : formatNumber(networkStats?.blockchain.totalTransactions || 0)}
          icon={ArrowRightLeft}
        />
        <StatCard
          label="Active Addresses"
          value={statsLoading ? '...' : formatNumber(networkStats?.blockchain.activeAddresses24h || 0)}
          icon={Users}
        />
        <StatCard
          label="Avg Block Time"
          value={statsLoading ? '...' : `${networkStats?.blockchain.avgBlockTime.toFixed(1)}s`}
          icon={Clock}
        />
      </div>

      {/* AI Network Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="AI Tasks"
          value={aiStats ? formatNumber(aiStats.totalTasks) : '...'}
          icon={Cpu}
        />
        <StatCard
          label="Active Providers"
          value={aiStats ? formatNumber(aiStats.activeProviders) : '...'}
          icon={Zap}
        />
        <StatCard
          label="Success Rate"
          value={aiStats ? `${aiStats.successRate.toFixed(1)}%` : '...'}
          icon={TrendingUp}
        />
        <StatCard
          label="Active Tasks"
          value={aiStats ? formatNumber(aiStats.activeTasks) : '...'}
          icon={Activity}
        />
      </div>

      {/* Recent Blocks & AI Tasks */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Recent Blocks */}
        <Card padding="none">
          <div className="p-6 pb-0">
            <CardHeader
              title={
                <div className="flex items-center gap-2">
                  <span>Recent Blocks</span>
                  {wsStatus === 'connected' && latestBlock && (
                    <Badge variant="success" className="animate-pulse">
                      <Radio className="h-3 w-3 mr-1" />
                      Live
                    </Badge>
                  )}
                </div>
              }
              action={
                <Link
                  to="/blocks"
                  className="text-sm text-xai-primary hover:underline"
                >
                  View All
                </Link>
              }
            />
          </div>
          {blocksLoading && displayBlocks.length === 0 ? (
            <div className="p-6">
              <Loading size="sm" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableHead>Height</TableHead>
                <TableHead>Hash</TableHead>
                <TableHead align="center">Txs</TableHead>
                <TableHead align="right">Time</TableHead>
              </TableHeader>
              <tbody>
                {displayBlocks.map((block) => (
                  <AnimatedTableRow key={block.hash} isNew={newBlockHashes.has(block.hash)}>
                    <TableCell>
                      <Link
                        to={`/block/${block.height}`}
                        className="text-xai-primary hover:underline font-medium"
                      >
                        {formatNumber(block.height)}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <HashLink hash={block.hash} to={`/block/${block.hash}`} />
                    </TableCell>
                    <TableCell align="center">
                      <Badge variant="info">{block.transactionCount || block.transactions?.length || 0}</Badge>
                    </TableCell>
                    <TableCell align="right" className="text-xai-muted">
                      {formatTimeAgo(block.timestamp)}
                    </TableCell>
                  </AnimatedTableRow>
                ))}
              </tbody>
            </Table>
          )}
        </Card>

        {/* Recent AI Tasks */}
        <Card padding="none">
          <div className="p-6 pb-0">
            <CardHeader
              title={
                <div className="flex items-center gap-2">
                  <span>Recent AI Tasks</span>
                  {wsStatus === 'connected' && latestAITask && (
                    <Badge variant="success" className="animate-pulse">
                      <Radio className="h-3 w-3 mr-1" />
                      Live
                    </Badge>
                  )}
                </div>
              }
              action={
                <Link
                  to="/ai"
                  className="text-sm text-xai-primary hover:underline"
                >
                  View All
                </Link>
              }
            />
          </div>
          {aiTasksLoading && displayAITasks.length === 0 ? (
            <div className="p-6">
              <Loading size="sm" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableHead>Task ID</TableHead>
                <TableHead>Model</TableHead>
                <TableHead align="center">Status</TableHead>
                <TableHead align="right">Cost</TableHead>
              </TableHeader>
              <tbody>
                {displayAITasks.map((task) => (
                  <AnimatedTableRow key={task.taskId} isNew={newTaskIds.has(task.taskId)}>
                    <TableCell>
                      <Link
                        to={`/ai/${task.taskId}`}
                        className="text-xai-primary hover:underline font-mono text-sm"
                      >
                        {task.taskId.slice(0, 12)}...
                      </Link>
                    </TableCell>
                    <TableCell className="text-xai-muted">
                      {task.aiModel}
                    </TableCell>
                    <TableCell align="center">
                      <Badge variant={getStatusVariant(task.status)}>
                        {task.status}
                      </Badge>
                    </TableCell>
                    <TableCell align="right" className="text-white">
                      {formatXAI(task.actualCost || task.costEstimate)}
                    </TableCell>
                  </AnimatedTableRow>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      </div>

      {/* Network Info */}
      <Card>
        <CardHeader title="Network Information" />
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="flex justify-between py-2 border-b border-xai-border">
            <span className="text-xai-muted">Network Hashrate</span>
            <span className="text-white font-medium">
              {networkStats?.blockchain.networkHashrate || 'N/A'}
            </span>
          </div>
          <div className="flex justify-between py-2 border-b border-xai-border">
            <span className="text-xai-muted">Difficulty</span>
            <span className="text-white font-medium">
              {networkStats ? formatNumber(networkStats.blockchain.difficulty) : 'N/A'}
            </span>
          </div>
          <div className="flex justify-between py-2 border-b border-xai-border">
            <span className="text-xai-muted">Total Supply</span>
            <span className="text-white font-medium">
              {networkStats ? formatXAI(networkStats.blockchain.totalSupply) : 'N/A'}
            </span>
          </div>
          <div className="flex justify-between py-2 border-b border-xai-border">
            <span className="text-xai-muted">Pending Transactions</span>
            <span className="text-white font-medium">
              {networkStats ? formatNumber(networkStats.mempool.pendingTransactions) : 'N/A'}
            </span>
          </div>
          <div className="flex justify-between py-2 border-b border-xai-border">
            <span className="text-xai-muted">Mempool Size</span>
            <span className="text-white font-medium">
              {networkStats ? `${networkStats.mempool.totalSizeKb.toFixed(1)} KB` : 'N/A'}
            </span>
          </div>
          <div className="flex justify-between py-2 border-b border-xai-border">
            <span className="text-xai-muted">AI Models in Use</span>
            <span className="text-white font-medium">
              {aiStats ? formatNumber(aiStats.modelsInUse) : 'N/A'}
            </span>
          </div>
        </div>
      </Card>

      {/* Devnet Resources */}
      <Card>
        <CardHeader title="Devnet Resources" />
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <a
            href="https://artifacts.xaiblockchain.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-3 p-4 rounded-lg bg-xai-darker border border-xai-border hover:border-xai-primary/50 transition-colors group"
          >
            <Download className="h-5 w-5 text-xai-primary shrink-0" />
            <div>
              <h3 className="text-white font-medium group-hover:text-xai-primary transition-colors">Artifacts</h3>
              <p className="text-sm text-xai-muted">Pre-built binaries and configs</p>
            </div>
          </a>
          <a
            href="/faucet"
            className="flex items-start gap-3 p-4 rounded-lg bg-xai-darker border border-xai-border hover:border-xai-primary/50 transition-colors group"
          >
            <Droplet className="h-5 w-5 text-xai-primary shrink-0" />
            <div>
              <h3 className="text-white font-medium group-hover:text-xai-primary transition-colors">Faucet</h3>
              <p className="text-sm text-xai-muted">Get test tokens</p>
            </div>
          </a>
          <a
            href="https://grafana.xaiblockchain.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-3 p-4 rounded-lg bg-xai-darker border border-xai-border hover:border-xai-primary/50 transition-colors group"
          >
            <BarChart2 className="h-5 w-5 text-xai-primary shrink-0" />
            <div>
              <h3 className="text-white font-medium group-hover:text-xai-primary transition-colors">Grafana</h3>
              <p className="text-sm text-xai-muted">Network monitoring</p>
            </div>
          </a>
          <a
            href="/docs"
            className="flex items-start gap-3 p-4 rounded-lg bg-xai-darker border border-xai-border hover:border-xai-primary/50 transition-colors group"
          >
            <FileCode className="h-5 w-5 text-xai-primary shrink-0" />
            <div>
              <h3 className="text-white font-medium group-hover:text-xai-primary transition-colors">API Docs</h3>
              <p className="text-sm text-xai-muted">REST API reference</p>
            </div>
          </a>
        </div>
      </Card>

    </div>
  );
}
