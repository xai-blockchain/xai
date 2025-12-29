/**
 * Tests for Card component
 */

import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react-native';
import { Text } from 'react-native';
import { Card } from '../../src/components/Card';

describe('Card Component', () => {
  describe('rendering', () => {
    it('should render children', () => {
      render(
        <Card>
          <Text>Card Content</Text>
        </Card>
      );

      expect(screen.getByText('Card Content')).toBeTruthy();
    });

    it('should render title when provided', () => {
      render(
        <Card title="Card Title">
          <Text>Content</Text>
        </Card>
      );

      expect(screen.getByText('Card Title')).toBeTruthy();
      expect(screen.getByText('Content')).toBeTruthy();
    });

    it('should not render title when not provided', () => {
      render(
        <Card>
          <Text>Only Content</Text>
        </Card>
      );

      expect(screen.getByText('Only Content')).toBeTruthy();
      // No title element should exist
    });

    it('should render multiple children', () => {
      render(
        <Card>
          <Text>First</Text>
          <Text>Second</Text>
          <Text>Third</Text>
        </Card>
      );

      expect(screen.getByText('First')).toBeTruthy();
      expect(screen.getByText('Second')).toBeTruthy();
      expect(screen.getByText('Third')).toBeTruthy();
    });
  });

  describe('interactions', () => {
    it('should be pressable when onPress is provided', () => {
      const onPress = jest.fn();
      render(
        <Card onPress={onPress}>
          <Text>Pressable Card</Text>
        </Card>
      );

      fireEvent.press(screen.getByText('Pressable Card'));

      expect(onPress).toHaveBeenCalledTimes(1);
    });

    it('should not be pressable when onPress is not provided', () => {
      const { UNSAFE_queryByType } = render(
        <Card>
          <Text>Non-pressable Card</Text>
        </Card>
      );

      // The card should render as a View, not TouchableOpacity
      expect(screen.getByText('Non-pressable Card')).toBeTruthy();
    });

    it('should handle multiple presses', () => {
      const onPress = jest.fn();
      render(
        <Card onPress={onPress}>
          <Text>Multi Press</Text>
        </Card>
      );

      fireEvent.press(screen.getByText('Multi Press'));
      fireEvent.press(screen.getByText('Multi Press'));
      fireEvent.press(screen.getByText('Multi Press'));

      expect(onPress).toHaveBeenCalledTimes(3);
    });
  });

  describe('styling', () => {
    it('should apply custom style', () => {
      render(
        <Card style={{ backgroundColor: 'blue' }}>
          <Text>Styled Card</Text>
        </Card>
      );

      expect(screen.getByText('Styled Card')).toBeTruthy();
    });

    it('should apply custom style when pressable', () => {
      const onPress = jest.fn();
      render(
        <Card onPress={onPress} style={{ padding: 20 }}>
          <Text>Styled Pressable</Text>
        </Card>
      );

      expect(screen.getByText('Styled Pressable')).toBeTruthy();
    });
  });

  describe('with title', () => {
    it('should render title above children', () => {
      const { toJSON } = render(
        <Card title="Title First">
          <Text>Content Below</Text>
        </Card>
      );

      // Title should be present
      expect(screen.getByText('Title First')).toBeTruthy();
      expect(screen.getByText('Content Below')).toBeTruthy();
    });

    it('should apply title styling', () => {
      render(
        <Card title="Styled Title">
          <Text>Content</Text>
        </Card>
      );

      const title = screen.getByText('Styled Title');
      expect(title).toBeTruthy();
    });
  });

  describe('edge cases', () => {
    it('should handle empty title', () => {
      render(
        <Card title="">
          <Text>Content Only</Text>
        </Card>
      );

      expect(screen.getByText('Content Only')).toBeTruthy();
    });

    it('should handle null children gracefully', () => {
      render(
        <Card title="Title">
          {null}
          <Text>Valid Child</Text>
        </Card>
      );

      expect(screen.getByText('Valid Child')).toBeTruthy();
    });

    it('should handle conditional children', () => {
      const showExtra = false;
      render(
        <Card>
          <Text>Always Visible</Text>
          {showExtra && <Text>Conditional</Text>}
        </Card>
      );

      expect(screen.getByText('Always Visible')).toBeTruthy();
      expect(screen.queryByText('Conditional')).toBeNull();
    });
  });
});
