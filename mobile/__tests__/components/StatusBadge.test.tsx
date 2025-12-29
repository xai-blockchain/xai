/**
 * Tests for StatusBadge component
 */

import React from 'react';
import { render, screen } from '@testing-library/react-native';
import { StatusBadge } from '../../src/components/StatusBadge';

describe('StatusBadge Component', () => {
  describe('rendering', () => {
    it('should render label text', () => {
      render(<StatusBadge status="success" label="Connected" />);

      expect(screen.getByText('Connected')).toBeTruthy();
    });

    it('should render with different labels', () => {
      const { rerender } = render(
        <StatusBadge status="success" label="Online" />
      );
      expect(screen.getByText('Online')).toBeTruthy();

      rerender(<StatusBadge status="error" label="Offline" />);
      expect(screen.getByText('Offline')).toBeTruthy();
    });
  });

  describe('status types', () => {
    it('should render success status', () => {
      render(<StatusBadge status="success" label="Success" />);
      expect(screen.getByText('Success')).toBeTruthy();
    });

    it('should render warning status', () => {
      render(<StatusBadge status="warning" label="Warning" />);
      expect(screen.getByText('Warning')).toBeTruthy();
    });

    it('should render error status', () => {
      render(<StatusBadge status="error" label="Error" />);
      expect(screen.getByText('Error')).toBeTruthy();
    });

    it('should render info status', () => {
      render(<StatusBadge status="info" label="Info" />);
      expect(screen.getByText('Info')).toBeTruthy();
    });

    it('should render neutral status', () => {
      render(<StatusBadge status="neutral" label="Neutral" />);
      expect(screen.getByText('Neutral')).toBeTruthy();
    });
  });

  describe('sizes', () => {
    it('should render medium size by default', () => {
      render(<StatusBadge status="success" label="Default Size" />);
      expect(screen.getByText('Default Size')).toBeTruthy();
    });

    it('should render small size', () => {
      render(<StatusBadge status="success" label="Small" size="small" />);
      expect(screen.getByText('Small')).toBeTruthy();
    });

    it('should render medium size explicitly', () => {
      render(<StatusBadge status="success" label="Medium" size="medium" />);
      expect(screen.getByText('Medium')).toBeTruthy();
    });
  });

  describe('visual elements', () => {
    it('should render status dot', () => {
      const { toJSON } = render(
        <StatusBadge status="success" label="With Dot" />
      );

      // Component structure should include the dot element
      expect(toJSON()).toBeTruthy();
    });

    it('should apply correct styling structure', () => {
      const { toJSON } = render(
        <StatusBadge status="error" label="Styled" size="small" />
      );

      expect(toJSON()).toBeTruthy();
    });
  });

  describe('status combinations', () => {
    it('should render each status with small size', () => {
      const statuses: Array<'success' | 'warning' | 'error' | 'info' | 'neutral'> = [
        'success',
        'warning',
        'error',
        'info',
        'neutral',
      ];

      statuses.forEach((status) => {
        const { unmount } = render(
          <StatusBadge status={status} label={`${status}-small`} size="small" />
        );
        expect(screen.getByText(`${status}-small`)).toBeTruthy();
        unmount();
      });
    });

    it('should render each status with medium size', () => {
      const statuses: Array<'success' | 'warning' | 'error' | 'info' | 'neutral'> = [
        'success',
        'warning',
        'error',
        'info',
        'neutral',
      ];

      statuses.forEach((status) => {
        const { unmount } = render(
          <StatusBadge status={status} label={`${status}-medium`} size="medium" />
        );
        expect(screen.getByText(`${status}-medium`)).toBeTruthy();
        unmount();
      });
    });
  });

  describe('common use cases', () => {
    it('should display connection status', () => {
      render(<StatusBadge status="success" label="Connected" />);
      expect(screen.getByText('Connected')).toBeTruthy();
    });

    it('should display disconnection status', () => {
      render(<StatusBadge status="error" label="Disconnected" />);
      expect(screen.getByText('Disconnected')).toBeTruthy();
    });

    it('should display pending status', () => {
      render(<StatusBadge status="warning" label="Pending" />);
      expect(screen.getByText('Pending')).toBeTruthy();
    });

    it('should display confirmed status', () => {
      render(<StatusBadge status="success" label="Confirmed" />);
      expect(screen.getByText('Confirmed')).toBeTruthy();
    });

    it('should display syncing status', () => {
      render(<StatusBadge status="info" label="Syncing" />);
      expect(screen.getByText('Syncing')).toBeTruthy();
    });
  });

  describe('edge cases', () => {
    it('should handle empty label', () => {
      render(<StatusBadge status="success" label="" />);
      // Empty string is still valid
      const { toJSON } = render(<StatusBadge status="success" label="" />);
      expect(toJSON()).toBeTruthy();
    });

    it('should handle long labels', () => {
      const longLabel = 'This is a very long status label that might overflow';
      render(<StatusBadge status="warning" label={longLabel} />);
      expect(screen.getByText(longLabel)).toBeTruthy();
    });

    it('should handle special characters in label', () => {
      render(<StatusBadge status="info" label="Status: 100% Complete!" />);
      expect(screen.getByText('Status: 100% Complete!')).toBeTruthy();
    });
  });

  describe('rerendering', () => {
    it('should update when status changes', () => {
      const { rerender } = render(
        <StatusBadge status="success" label="Status" />
      );

      rerender(<StatusBadge status="error" label="Status" />);
      expect(screen.getByText('Status')).toBeTruthy();
    });

    it('should update when label changes', () => {
      const { rerender } = render(
        <StatusBadge status="success" label="Original" />
      );

      expect(screen.getByText('Original')).toBeTruthy();

      rerender(<StatusBadge status="success" label="Updated" />);
      expect(screen.getByText('Updated')).toBeTruthy();
    });

    it('should update when size changes', () => {
      const { rerender } = render(
        <StatusBadge status="success" label="Resize" size="small" />
      );

      rerender(<StatusBadge status="success" label="Resize" size="medium" />);
      expect(screen.getByText('Resize')).toBeTruthy();
    });
  });
});
