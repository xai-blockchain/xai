/**
 * Tests for Input component
 */

import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react-native';
import { Text } from 'react-native';
import { Input } from '../../src/components/Input';

describe('Input Component', () => {
  describe('rendering', () => {
    it('should render basic input', () => {
      render(<Input placeholder="Enter text" />);

      expect(screen.getByPlaceholderText('Enter text')).toBeTruthy();
    });

    it('should render with label', () => {
      render(<Input label="Username" placeholder="Enter username" />);

      expect(screen.getByText('Username')).toBeTruthy();
      expect(screen.getByPlaceholderText('Enter username')).toBeTruthy();
    });

    it('should render without label', () => {
      render(<Input placeholder="No label" />);

      expect(screen.queryByText('Username')).toBeNull();
      expect(screen.getByPlaceholderText('No label')).toBeTruthy();
    });

    it('should render with right element', () => {
      const rightElement = <Text testID="right-elem">Right</Text>;
      render(<Input placeholder="With right" rightElement={rightElement} />);

      expect(screen.getByTestId('right-elem')).toBeTruthy();
    });
  });

  describe('value handling', () => {
    it('should display value', () => {
      render(<Input value="test value" placeholder="Enter" />);

      expect(screen.getByDisplayValue('test value')).toBeTruthy();
    });

    it('should call onChangeText when text changes', () => {
      const onChangeText = jest.fn();
      render(
        <Input
          placeholder="Type here"
          onChangeText={onChangeText}
        />
      );

      fireEvent.changeText(screen.getByPlaceholderText('Type here'), 'new text');

      expect(onChangeText).toHaveBeenCalledWith('new text');
    });

    it('should update on multiple changes', () => {
      const onChangeText = jest.fn();
      render(<Input placeholder="Test" onChangeText={onChangeText} />);

      const input = screen.getByPlaceholderText('Test');

      fireEvent.changeText(input, 'first');
      fireEvent.changeText(input, 'second');
      fireEvent.changeText(input, 'third');

      expect(onChangeText).toHaveBeenCalledTimes(3);
      expect(onChangeText).toHaveBeenLastCalledWith('third');
    });
  });

  describe('error state', () => {
    it('should display error message', () => {
      render(<Input placeholder="Error input" error="This field is required" />);

      expect(screen.getByText('This field is required')).toBeTruthy();
    });

    it('should not display error when not provided', () => {
      render(<Input placeholder="No error" />);

      expect(screen.queryByText('This field is required')).toBeNull();
    });

    it('should apply error styling', () => {
      render(<Input placeholder="Error styled" error="Invalid" />);

      expect(screen.getByText('Invalid')).toBeTruthy();
    });

    it('should clear error when error prop removed', () => {
      const { rerender } = render(
        <Input placeholder="Test" error="Error shown" />
      );

      expect(screen.getByText('Error shown')).toBeTruthy();

      rerender(<Input placeholder="Test" />);

      expect(screen.queryByText('Error shown')).toBeNull();
    });
  });

  describe('TextInput props passthrough', () => {
    it('should handle secureTextEntry', () => {
      render(<Input placeholder="Password" secureTextEntry />);

      const input = screen.getByPlaceholderText('Password');
      expect(input.props.secureTextEntry).toBe(true);
    });

    it('should handle autoCapitalize', () => {
      render(<Input placeholder="Lowercase" autoCapitalize="none" />);

      const input = screen.getByPlaceholderText('Lowercase');
      expect(input.props.autoCapitalize).toBe('none');
    });

    it('should handle autoCorrect', () => {
      render(<Input placeholder="No correct" autoCorrect={false} />);

      const input = screen.getByPlaceholderText('No correct');
      expect(input.props.autoCorrect).toBe(false);
    });

    it('should handle keyboardType', () => {
      render(<Input placeholder="Number" keyboardType="numeric" />);

      const input = screen.getByPlaceholderText('Number');
      expect(input.props.keyboardType).toBe('numeric');
    });

    it('should handle returnKeyType', () => {
      render(<Input placeholder="Done" returnKeyType="done" />);

      const input = screen.getByPlaceholderText('Done');
      expect(input.props.returnKeyType).toBe('done');
    });

    it('should handle onSubmitEditing', () => {
      const onSubmit = jest.fn();
      render(<Input placeholder="Submit" onSubmitEditing={onSubmit} />);

      fireEvent(screen.getByPlaceholderText('Submit'), 'submitEditing');

      expect(onSubmit).toHaveBeenCalled();
    });
  });

  describe('focus handling', () => {
    it('should handle onFocus', () => {
      const onFocus = jest.fn();
      render(<Input placeholder="Focus" onFocus={onFocus} />);

      fireEvent(screen.getByPlaceholderText('Focus'), 'focus');

      expect(onFocus).toHaveBeenCalled();
    });

    it('should handle onBlur', () => {
      const onBlur = jest.fn();
      render(<Input placeholder="Blur" onBlur={onBlur} />);

      fireEvent(screen.getByPlaceholderText('Blur'), 'blur');

      expect(onBlur).toHaveBeenCalled();
    });
  });

  describe('styling', () => {
    it('should apply container style', () => {
      render(
        <Input
          placeholder="Styled"
          containerStyle={{ margin: 10 }}
        />
      );

      expect(screen.getByPlaceholderText('Styled')).toBeTruthy();
    });

    it('should apply input style', () => {
      render(
        <Input
          placeholder="Input styled"
          style={{ fontSize: 20 }}
        />
      );

      expect(screen.getByPlaceholderText('Input styled')).toBeTruthy();
    });
  });

  describe('accessibility', () => {
    it('should associate label with input', () => {
      render(<Input label="Email Address" placeholder="Enter email" />);

      expect(screen.getByText('Email Address')).toBeTruthy();
      expect(screen.getByPlaceholderText('Enter email')).toBeTruthy();
    });
  });

  describe('edge cases', () => {
    it('should handle empty value', () => {
      render(<Input value="" placeholder="Empty" />);

      expect(screen.getByPlaceholderText('Empty')).toBeTruthy();
    });

    it('should handle undefined onChangeText', () => {
      render(<Input placeholder="No handler" />);

      const input = screen.getByPlaceholderText('No handler');

      // Should not throw
      expect(() => {
        fireEvent.changeText(input, 'text');
      }).not.toThrow();
    });

    it('should handle special characters in error', () => {
      render(
        <Input
          placeholder="Special"
          error="Error: <invalid> 'chars' & symbols"
        />
      );

      expect(screen.getByText("Error: <invalid> 'chars' & symbols")).toBeTruthy();
    });
  });
});
