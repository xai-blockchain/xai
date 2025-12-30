import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { Home } from './pages/Home';
import { Blocks } from './pages/Blocks';
import { BlockDetail } from './pages/BlockDetail';
import { Transactions } from './pages/Transactions';
import { TransactionDetail } from './pages/TransactionDetail';
import { Address } from './pages/Address';
import { AITasks } from './pages/AITasks';
import { AITaskDetail } from './pages/AITaskDetail';
import { NotFound } from './pages/NotFound';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10000, // 10 seconds
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="blocks" element={<Blocks />} />
            <Route path="block/:blockId" element={<BlockDetail />} />
            <Route path="transactions" element={<Transactions />} />
            <Route path="tx/:txid" element={<TransactionDetail />} />
            <Route path="address/:address" element={<Address />} />
            <Route path="ai" element={<AITasks />} />
            <Route path="ai/:taskId" element={<AITaskDetail />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
