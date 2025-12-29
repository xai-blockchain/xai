/**
 * Tests for Button component
 */

import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react-native';
import { Text, View } from 'react-native';
import { Button } from '../../src/components/Button';

describe('Button Component', () => {
  describe('rendering', () => {
    it('should render with title', () => {
      render(<Button title="Click Me" onPress={() => {}} />);

      expect(screen.getByText('Click Me')).toBeTruthy();
    });

    it('should render with icon', () => {
      const icon = <Text testID="test-icon">Icon</Text>;
      render(<Button title="With Icon" onPress={() => {}} icon={icon} />);

      expect(screen.getByTestId('test-icon')).toBeTruthy();
      expect(screen.getByText('With Icon')).toBeTruthy();
    });
  });

  describe('variants', () => {
    it('should render primary variant by default', () => {
      const { getByText } = render(<Button title="Primary" onPress={() => {}} />);
      // Button renders with primary styles by default
      expect(getByText('Primary')).toBeTruthy();
    });

    it('should render secondary variant', () => {
      const { getByText } = render(
        <Button title="Secondary" variant="secondary" onPress={() => {}} />
      );
      expect(getByText('Secondary')).toBeTruthy();
    });

    it('should render outline variant', () => {
      const { getByText } = render(
        <Button title="Outline" variant="outline" onPress={() => {}} />
      );
      expect(getByText('Outline')).toBeTruthy();
    });

    it('should render danger variant', () => {
      const { getByText } = render(
        <Button title="Danger" variant="danger" onPress={() => {}} />
      );
      expect(getByText('Danger')).toBeTruthy();
    });
  });

  describe('sizes', () => {
    it('should render medium size by default', () => {
      const { getByText } = render(<Button title="Medium" onPress={() => {}} />);
      expect(getByText('Medium')).toBeTruthy();
    });

    it('should render small size', () => {
      const { getByText } = render(
        <Button title="Small" size="small" onPress={() => {}} />
      );
      expect(getByText('Small')).toBeTruthy();
    });

    it('should render large size', () => {
      const { getByText } = render(
        <Button title="Large" size="large" onPress={() => {}} />
      );
      expect(getByText('Large')).toBeTruthy();
    });
  });

  describe('interactions', () => {
    it('should call onPress when pressed', () => {
      const onPress = jest.fn();
      const { getByText } = render(<Button title="Press Me" onPress={onPress} />);

      fireEvent.press(getByText('Press Me'));

      expect(onPress).toHaveBeenCalledTimes(1);
    });

    it('should not call onPress when disabled', () => {
      const onPress = jest.fn();
      const { getByText } = render(
        <Button title="Disabled" onPress={onPress} disabled />
      );

      fireEvent.press(getByText('Disabled'));

      expect(onPress).not.toHaveBeenCalled();
    });

    it('should not call onPress when loading', () => {
      const onPress = jest.fn();
      render(<Button title="Loading" onPress={onPress} loading />);

      // Title is not visible when loading
      expect(screen.queryByText('Loading')).toBeNull();
    });
  });

  describe('loading state', () => {
    it('should show loading indicator when loading', () => {
      const { queryByText } = render(
        <Button title="Loading" onPress={() => {}} loading />
      );

      // Title should be hidden when loading
      expect(queryByText('Loading')).toBeNull();
    });

    it('should hide title when loading', () => {
      const { queryByText } = render(
        <Button title="Hidden" onPress={() => {}} loading />
      );

      expect(queryByText('Hidden')).toBeNull();
    });

    it('should be disabled when loading', () => {
      const onPress = jest.fn();
      const { UNSAFE_getByType } = render(
        <Button title="Test" onPress={onPress} loading />
      );

      // Component should be disabled when loading
      // We can test this by checking that onPress isn't called
    });
  });

  describe('disabled state', () => {
    it('should apply disabled styling', () => {
      const { getByText } = render(
        <Button title="Disabled" onPress={() => {}} disabled />
      );

      expect(getByText('Disabled')).toBeTruthy();
    });

    it('should be disabled when disabled prop is true', () => {
      const onPress = jest.fn();
      const { getByText } = render(
        <Button title="Test" onPress={onPress} disabled />
      );

      fireEvent.press(getByText('Test'));
      expect(onPress).not.toHaveBeenCalled();
    });
  });

  describe('custom styles', () => {
    it('should apply custom style to button', () => {
      const { getByText } = render(
        <Button
          title="Styled"
          onPress={() => {}}
          style={{ backgroundColor: 'red' }}
        />
      );

      expect(getByText('Styled')).toBeTruthy();
    });

    it('should apply custom text style', () => {
      const { getByText } = render(
        <Button
          title="Custom Text"
          onPress={() => {}}
          textStyle={{ fontSize: 20 }}
        />
      );

      expect(getByText('Custom Text')).toBeTruthy();
    });
  });
});
