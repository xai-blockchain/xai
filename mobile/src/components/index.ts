/**
 * XAI Mobile App - Components Index
 *
 * Centralized export for all UI components.
 */

// Core components
export { Button, type ButtonVariant, type ButtonSize } from './Button';
export { Card, BalanceCard, StatCard, type CardVariant } from './Card';
export { Input, SearchInput, PasswordInput, AmountInput } from './Input';

// Data display components
export { TransactionItem } from './TransactionItem';
export { BlockItem, LatestBlockCard } from './BlockItem';
export {
  StatusBadge,
  ConnectionBadge,
  TransactionStatusBadge,
  NetworkPressureBadge,
  type StatusType,
} from './StatusBadge';

// Loading and skeleton components
export {
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonTransaction,
  SkeletonBalance,
  SkeletonBlock,
} from './Skeleton';

// Empty states
export {
  EmptyState,
  NoTransactionsEmpty,
  NoWalletEmpty,
  ConnectionErrorEmpty,
  SearchEmpty,
  NoResultsEmpty,
  type EmptyStateType,
} from './EmptyState';

// Dialogs and modals
export {
  ConfirmDialog,
  DeleteWalletDialog,
  SendTransactionDialog,
  ExportKeyDialog,
  type DialogVariant,
} from './ConfirmDialog';

// Progress indicators
export {
  Spinner,
  DotsLoader,
  ProgressBar,
  StepProgress,
  LoadingOverlay,
} from './ProgressIndicator';

// Icons
export { Icon, type IconName } from './Icon';

// Layout containers
export {
  ScreenContainer,
  TabScreenContainer,
  ModalScreenContainer,
  FullScreenContainer,
} from './ScreenContainer';

// Onboarding
export { Onboarding, OnboardingTip } from './Onboarding';
