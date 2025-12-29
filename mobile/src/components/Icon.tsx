/**
 * XAI Icon Component
 *
 * SVG-based icons for the mobile app.
 * Uses react-native-svg for cross-platform rendering.
 */

import React from 'react';
import { View, ViewStyle } from 'react-native';
import Svg, { Path, Circle, Rect, G, Line } from 'react-native-svg';
import { useTheme } from '../theme';

export type IconName =
  | 'home'
  | 'wallet'
  | 'send'
  | 'receive'
  | 'explorer'
  | 'settings'
  | 'copy'
  | 'check'
  | 'close'
  | 'chevron-right'
  | 'chevron-left'
  | 'chevron-down'
  | 'chevron-up'
  | 'arrow-up'
  | 'arrow-down'
  | 'arrow-right'
  | 'arrow-left'
  | 'refresh'
  | 'qr-code'
  | 'scan'
  | 'warning'
  | 'error'
  | 'info'
  | 'success'
  | 'key'
  | 'lock'
  | 'unlock'
  | 'eye'
  | 'eye-off'
  | 'trash'
  | 'edit'
  | 'share'
  | 'link'
  | 'block'
  | 'transaction'
  | 'clock'
  | 'user'
  | 'plus'
  | 'minus'
  | 'search'
  | 'filter'
  | 'menu'
  | 'more'
  | 'star'
  | 'heart'
  | 'bell'
  | 'xai-logo';

interface IconProps {
  name: IconName;
  size?: number;
  color?: string;
  style?: ViewStyle;
}

export function Icon({ name, size = 24, color, style }: IconProps) {
  const theme = useTheme();
  const iconColor = color || theme.colors.text;

  const icons: Record<IconName, React.ReactNode> = {
    'home': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M3 9L12 2L21 9V20C21 20.5304 20.7893 21.0391 20.4142 21.4142C20.0391 21.7893 19.5304 22 19 22H5C4.46957 22 3.96086 21.7893 3.58579 21.4142C3.21071 21.0391 3 20.5304 3 20V9Z"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M9 22V12H15V22"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'wallet': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M21 4H3C1.89543 4 1 4.89543 1 6V18C1 19.1046 1.89543 20 3 20H21C22.1046 20 23 19.1046 23 18V6C23 4.89543 22.1046 4 21 4Z"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M1 10H23"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Circle cx="18" cy="15" r="1.5" fill={iconColor} />
      </Svg>
    ),
    'send': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M22 2L11 13"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M22 2L15 22L11 13L2 9L22 2Z"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'receive': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M12 5V19"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M19 12L12 19L5 12"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'explorer': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Rect x="3" y="3" width="7" height="7" rx="1" stroke={iconColor} strokeWidth={2} />
        <Rect x="14" y="3" width="7" height="7" rx="1" stroke={iconColor} strokeWidth={2} />
        <Rect x="3" y="14" width="7" height="7" rx="1" stroke={iconColor} strokeWidth={2} />
        <Rect x="14" y="14" width="7" height="7" rx="1" stroke={iconColor} strokeWidth={2} />
      </Svg>
    ),
    'settings': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Circle cx="12" cy="12" r="3" stroke={iconColor} strokeWidth={2} />
        <Path
          d="M19.4 15C19.2669 15.3016 19.2272 15.6362 19.286 15.9606C19.3448 16.285 19.4995 16.5843 19.73 16.82L19.79 16.88C19.976 17.0657 20.1235 17.2863 20.2241 17.5291C20.3248 17.7719 20.3766 18.0322 20.3766 18.295C20.3766 18.5578 20.3248 18.8181 20.2241 19.0609C20.1235 19.3037 19.976 19.5243 19.79 19.71C19.6043 19.896 19.3837 20.0435 19.1409 20.1441C18.8981 20.2448 18.6378 20.2966 18.375 20.2966C18.1122 20.2966 17.8519 20.2448 17.6091 20.1441C17.3663 20.0435 17.1457 19.896 16.96 19.71L16.9 19.65C16.6643 19.4195 16.365 19.2648 16.0406 19.206C15.7162 19.1472 15.3816 19.1869 15.08 19.32C14.7842 19.4468 14.532 19.6572 14.3543 19.9255C14.1766 20.1938 14.0813 20.5082 14.08 20.83V21C14.08 21.5304 13.8693 22.0391 13.4942 22.4142C13.1191 22.7893 12.6104 23 12.08 23C11.5496 23 11.0409 22.7893 10.6658 22.4142C10.2907 22.0391 10.08 21.5304 10.08 21V20.91C10.0723 20.579 9.96512 20.258 9.77251 19.9887C9.5799 19.7194 9.31074 19.5143 9 19.4C8.69838 19.2669 8.36381 19.2272 8.03941 19.286C7.71502 19.3448 7.41568 19.4995 7.18 19.73L7.12 19.79C6.93425 19.976 6.71368 20.1235 6.47088 20.2241C6.22808 20.3248 5.96783 20.3766 5.705 20.3766C5.44217 20.3766 5.18192 20.3248 4.93912 20.2241C4.69632 20.1235 4.47575 19.976 4.29 19.79C4.10405 19.6043 3.95653 19.3837 3.85588 19.1409C3.75523 18.8981 3.70343 18.6378 3.70343 18.375C3.70343 18.1122 3.75523 17.8519 3.85588 17.6091C3.95653 17.3663 4.10405 17.1457 4.29 16.96L4.35 16.9C4.58054 16.6643 4.73519 16.365 4.794 16.0406C4.85282 15.7162 4.81312 15.3816 4.68 15.08C4.55324 14.7842 4.34276 14.532 4.07447 14.3543C3.80618 14.1766 3.49179 14.0813 3.17 14.08H3C2.46957 14.08 1.96086 13.8693 1.58579 13.4942C1.21071 13.1191 1 12.6104 1 12.08C1 11.5496 1.21071 11.0409 1.58579 10.6658C1.96086 10.2907 2.46957 10.08 3 10.08H3.09C3.42099 10.0723 3.742 9.96512 4.0113 9.77251C4.28059 9.5799 4.48572 9.31074 4.6 9C4.73312 8.69838 4.77282 8.36381 4.714 8.03941C4.65519 7.71502 4.50054 7.41568 4.27 7.18L4.21 7.12C4.02405 6.93425 3.87653 6.71368 3.77588 6.47088C3.67523 6.22808 3.62343 5.96783 3.62343 5.705C3.62343 5.44217 3.67523 5.18192 3.77588 4.93912C3.87653 4.69632 4.02405 4.47575 4.21 4.29C4.39575 4.10405 4.61632 3.95653 4.85912 3.85588C5.10192 3.75523 5.36217 3.70343 5.625 3.70343C5.88783 3.70343 6.14808 3.75523 6.39088 3.85588C6.63368 3.95653 6.85425 4.10405 7.04 4.29L7.1 4.35C7.33568 4.58054 7.63502 4.73519 7.95941 4.794C8.28381 4.85282 8.61838 4.81312 8.92 4.68H9C9.29577 4.55324 9.54802 4.34276 9.72569 4.07447C9.90337 3.80618 9.99872 3.49179 10 3.17V3C10 2.46957 10.2107 1.96086 10.5858 1.58579C10.9609 1.21071 11.4696 1 12 1C12.5304 1 13.0391 1.21071 13.4142 1.58579C13.7893 1.96086 14 2.46957 14 3V3.09C14.0013 3.41179 14.0966 3.72618 14.2743 3.99447C14.452 4.26276 14.7042 4.47324 15 4.6C15.3016 4.73312 15.6362 4.77282 15.9606 4.714C16.285 4.65519 16.5843 4.50054 16.82 4.27L16.88 4.21C17.0657 4.02405 17.2863 3.87653 17.5291 3.77588C17.7719 3.67523 18.0322 3.62343 18.295 3.62343C18.5578 3.62343 18.8181 3.67523 19.0609 3.77588C19.3037 3.87653 19.5243 4.02405 19.71 4.21C19.896 4.39575 20.0435 4.61632 20.1441 4.85912C20.2448 5.10192 20.2966 5.36217 20.2966 5.625C20.2966 5.88783 20.2448 6.14808 20.1441 6.39088C20.0435 6.63368 19.896 6.85425 19.71 7.04L19.65 7.1C19.4195 7.33568 19.2648 7.63502 19.206 7.95941C19.1472 8.28381 19.1869 8.61838 19.32 8.92V9C19.4468 9.29577 19.6572 9.54802 19.9255 9.72569C20.1938 9.90337 20.5082 9.99872 20.83 10H21C21.5304 10 22.0391 10.2107 22.4142 10.5858C22.7893 10.9609 23 11.4696 23 12C23 12.5304 22.7893 13.0391 22.4142 13.4142C22.0391 13.7893 21.5304 14 21 14H20.91C20.5882 14.0013 20.2738 14.0966 20.0055 14.2743C19.7372 14.452 19.5268 14.7042 19.4 15Z"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'copy': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Rect x="9" y="9" width="13" height="13" rx="2" stroke={iconColor} strokeWidth={2} />
        <Path
          d="M5 15H4C2.89543 15 2 14.1046 2 13V4C2 2.89543 2.89543 2 4 2H13C14.1046 2 15 2.89543 15 4V5"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'check': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M20 6L9 17L4 12"
          stroke={iconColor}
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'close': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M18 6L6 18M6 6L18 18"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'chevron-right': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M9 18L15 12L9 6"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'chevron-left': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M15 18L9 12L15 6"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'chevron-down': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M6 9L12 15L18 9"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'chevron-up': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M18 15L12 9L6 15"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'arrow-up': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M12 19V5M5 12L12 5L19 12"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'arrow-down': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M12 5V19M19 12L12 19L5 12"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'arrow-right': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M5 12H19M12 5L19 12L12 19"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'arrow-left': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M19 12H5M12 19L5 12L12 5"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'refresh': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M1 4V10H7"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M23 20V14H17"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M20.49 9C19.9828 7.56678 19.1209 6.2854 17.9845 5.27542C16.8482 4.26543 15.4745 3.55976 13.9917 3.22426C12.5089 2.88875 10.9652 2.93434 9.50481 3.35677C8.04437 3.77921 6.71475 4.56471 5.64 5.64L1 10M23 14L18.36 18.36C17.2853 19.4353 15.9556 20.2208 14.4952 20.6432C13.0348 21.0657 11.4911 21.1112 10.0083 20.7757C8.52547 20.4402 7.1518 19.7346 6.01547 18.7246C4.87913 17.7146 4.01717 16.4332 3.51 15"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'qr-code': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Rect x="3" y="3" width="7" height="7" stroke={iconColor} strokeWidth={2} />
        <Rect x="14" y="3" width="7" height="7" stroke={iconColor} strokeWidth={2} />
        <Rect x="3" y="14" width="7" height="7" stroke={iconColor} strokeWidth={2} />
        <Rect x="14" y="14" width="3" height="3" fill={iconColor} />
        <Rect x="18" y="14" width="3" height="3" fill={iconColor} />
        <Rect x="14" y="18" width="3" height="3" fill={iconColor} />
        <Rect x="18" y="18" width="3" height="3" fill={iconColor} />
      </Svg>
    ),
    'scan': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M2 7V2H7M17 2H22V7M22 17V22H17M7 22H2V17"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Line x1="4" y1="12" x2="20" y2="12" stroke={iconColor} strokeWidth={2} strokeLinecap="round" />
      </Svg>
    ),
    'warning': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M10.29 3.86L1.82 18C1.64 18.3 1.55 18.64 1.55 19C1.55 19.36 1.64 19.7 1.82 20C2 20.3 2.26 20.56 2.56 20.74C2.86 20.92 3.2 21.01 3.55 21H20.49C20.84 21.01 21.18 20.92 21.48 20.74C21.78 20.56 22.04 20.3 22.22 20C22.4 19.7 22.49 19.36 22.49 19C22.49 18.64 22.4 18.3 22.22 18L13.75 3.86C13.57 3.56 13.31 3.32 13 3.15C12.69 2.98 12.35 2.89 12 2.89C11.65 2.89 11.31 2.98 11 3.15C10.69 3.32 10.43 3.56 10.29 3.86Z"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Line x1="12" y1="9" x2="12" y2="13" stroke={iconColor} strokeWidth={2} strokeLinecap="round" />
        <Circle cx="12" cy="17" r="1" fill={iconColor} />
      </Svg>
    ),
    'error': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Circle cx="12" cy="12" r="10" stroke={iconColor} strokeWidth={2} />
        <Path
          d="M15 9L9 15M9 9L15 15"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'info': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Circle cx="12" cy="12" r="10" stroke={iconColor} strokeWidth={2} />
        <Line x1="12" y1="16" x2="12" y2="12" stroke={iconColor} strokeWidth={2} strokeLinecap="round" />
        <Circle cx="12" cy="8" r="1" fill={iconColor} />
      </Svg>
    ),
    'success': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Circle cx="12" cy="12" r="10" stroke={iconColor} strokeWidth={2} />
        <Path
          d="M9 12L11 14L15 10"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'key': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M21 2L19 4M11.39 11.61C12.2253 12.4195 12.7934 13.4633 13.0213 14.6025C13.2492 15.7417 13.1262 16.9238 12.6678 17.9915C12.2094 19.0592 11.4368 19.9623 10.4535 20.5813C9.47027 21.2003 8.32126 21.5063 7.15837 21.4573C5.99548 21.4083 4.87603 21.0067 3.94777 20.3078C3.0195 19.609 2.32602 18.6451 1.95982 17.5449C1.59363 16.4447 1.57185 15.26 1.89751 14.1478C2.22317 13.0356 2.8813 12.0465 3.78 11.31C4.93737 10.3617 6.41077 9.88095 7.90381 9.96026C9.39684 10.0396 10.8129 10.6734 11.86 11.74L16 8L19 11L21 9L21 2Z"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'lock': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Rect x="3" y="11" width="18" height="11" rx="2" stroke={iconColor} strokeWidth={2} />
        <Path
          d="M7 11V7C7 4.23858 9.23858 2 12 2C14.7614 2 17 4.23858 17 7V11"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'unlock': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Rect x="3" y="11" width="18" height="11" rx="2" stroke={iconColor} strokeWidth={2} />
        <Path
          d="M7 11V7C7 4.23858 9.23858 2 12 2C13.9587 2 15.6576 3.11929 16.5 4.75"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'eye': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M1 12C1 12 5 4 12 4C19 4 23 12 23 12C23 12 19 20 12 20C5 20 1 12 1 12Z"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Circle cx="12" cy="12" r="3" stroke={iconColor} strokeWidth={2} />
      </Svg>
    ),
    'eye-off': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M17.94 17.94C16.2306 19.243 14.1491 19.9649 12 20C5 20 1 12 1 12C2.24389 9.68192 3.96914 7.65663 6.06 6.06M9.9 4.24C10.5883 4.0789 11.2931 3.99836 12 4C19 4 23 12 23 12C22.393 13.1356 21.6691 14.2048 20.84 15.19M14.12 14.12C13.8454 14.4148 13.5141 14.6512 13.1462 14.8151C12.7782 14.9791 12.3809 15.0673 11.9781 15.0744C11.5753 15.0815 11.1752 15.0074 10.8016 14.8565C10.4281 14.7056 10.0887 14.4811 9.80385 14.1962C9.51897 13.9113 9.29439 13.5719 9.14351 13.1984C8.99262 12.8248 8.91853 12.4247 8.92563 12.0219C8.93274 11.6191 9.02091 11.2218 9.18488 10.8538C9.34884 10.4859 9.58525 10.1546 9.88 9.88"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M1 1L23 23"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'trash': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M3 6H5H21"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'edit': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M11 4H4C3.46957 4 2.96086 4.21071 2.58579 4.58579C2.21071 4.96086 2 5.46957 2 6V20C2 20.5304 2.21071 21.0391 2.58579 21.4142C2.96086 21.7893 3.46957 22 4 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V13"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M18.5 2.5C18.8978 2.10217 19.4374 1.87868 20 1.87868C20.5626 1.87868 21.1022 2.10217 21.5 2.5C21.8978 2.89782 22.1213 3.43739 22.1213 4C22.1213 4.56261 21.8978 5.10217 21.5 5.5L12 15L8 16L9 12L18.5 2.5Z"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'share': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Circle cx="18" cy="5" r="3" stroke={iconColor} strokeWidth={2} />
        <Circle cx="6" cy="12" r="3" stroke={iconColor} strokeWidth={2} />
        <Circle cx="18" cy="19" r="3" stroke={iconColor} strokeWidth={2} />
        <Line x1="8.59" y1="13.51" x2="15.42" y2="17.49" stroke={iconColor} strokeWidth={2} />
        <Line x1="15.41" y1="6.51" x2="8.59" y2="10.49" stroke={iconColor} strokeWidth={2} />
      </Svg>
    ),
    'link': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M10 13C10.4295 13.5741 10.9774 14.0491 11.6066 14.3929C12.2357 14.7367 12.9315 14.9411 13.6467 14.9923C14.3618 15.0435 15.0796 14.9403 15.7513 14.6897C16.4231 14.4392 17.0331 14.047 17.54 13.54L20.54 10.54C21.4508 9.59695 21.9548 8.33394 21.9434 7.02296C21.932 5.71198 21.4061 4.45791 20.479 3.53087C19.552 2.60383 18.298 2.0779 16.987 2.0665C15.676 2.0551 14.413 2.55912 13.47 3.47L11.75 5.18"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M14 11C13.5705 10.4259 13.0226 9.95083 12.3934 9.60707C11.7642 9.26331 11.0685 9.05889 10.3533 9.00768C9.63816 8.95646 8.92037 9.05964 8.24861 9.31023C7.57685 9.56082 6.96684 9.95304 6.45996 10.46L3.45996 13.46C2.54917 14.4031 2.04515 15.6661 2.05655 16.977C2.06795 18.288 2.59387 19.5421 3.52091 20.4691C4.44795 21.3962 5.70202 21.9221 7.013 21.9335C8.32398 21.9449 9.58699 21.4409 10.53 20.53L12.24 18.82"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'block': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M21 16V8C20.9996 7.6493 20.9071 7.30481 20.7315 7.00116C20.556 6.69751 20.3037 6.44536 20 6.27L13 2.27C12.696 2.09446 12.3511 2.00205 12 2.00205C11.6489 2.00205 11.304 2.09446 11 2.27L4 6.27C3.69626 6.44536 3.44398 6.69751 3.26846 7.00116C3.09294 7.30481 3.00036 7.6493 3 8V16C3.00036 16.3507 3.09294 16.6952 3.26846 16.9988C3.44398 17.3025 3.69626 17.5546 4 17.73L11 21.73C11.304 21.9055 11.6489 21.998 12 21.998C12.3511 21.998 12.696 21.9055 13 21.73L20 17.73C20.3037 17.5546 20.556 17.3025 20.7315 16.9988C20.9071 16.6952 20.9996 16.3507 21 16Z"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M3.27 6.96L12 12.01L20.73 6.96"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M12 22.08V12"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'transaction': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M17 1L21 5L17 9"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M3 11V9C3 7.93913 3.42143 6.92172 4.17157 6.17157C4.92172 5.42143 5.93913 5 7 5H21"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M7 23L3 19L7 15"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M21 13V15C21 16.0609 20.5786 17.0783 19.8284 17.8284C19.0783 18.5786 18.0609 19 17 19H3"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'clock': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Circle cx="12" cy="12" r="10" stroke={iconColor} strokeWidth={2} />
        <Path
          d="M12 6V12L16 14"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'user': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Circle cx="12" cy="7" r="4" stroke={iconColor} strokeWidth={2} />
      </Svg>
    ),
    'plus': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M12 5V19M5 12H19"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'minus': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M5 12H19"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'search': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Circle cx="11" cy="11" r="8" stroke={iconColor} strokeWidth={2} />
        <Path
          d="M21 21L16.65 16.65"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'filter': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M22 3H2L10 12.46V19L14 21V12.46L22 3Z"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'menu': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M3 12H21M3 6H21M3 18H21"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'more': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Circle cx="12" cy="12" r="1.5" fill={iconColor} />
        <Circle cx="12" cy="5" r="1.5" fill={iconColor} />
        <Circle cx="12" cy="19" r="1.5" fill={iconColor} />
      </Svg>
    ),
    'star': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'heart': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M20.84 4.61C20.3292 4.09924 19.7228 3.69397 19.0554 3.41708C18.3879 3.14019 17.6725 2.99738 16.95 2.99738C16.2275 2.99738 15.5121 3.14019 14.8446 3.41708C14.1772 3.69397 13.5708 4.09924 13.06 4.61L12 5.67L10.94 4.61C9.9083 3.57831 8.50903 2.99789 7.05 2.99789C5.59096 2.99789 4.19169 3.57831 3.16 4.61C2.1283 5.64169 1.54788 7.04097 1.54788 8.5C1.54788 9.95903 2.1283 11.3583 3.16 12.39L4.22 13.45L12 21.23L19.78 13.45L20.84 12.39C21.3508 11.8792 21.756 11.2728 22.0329 10.6054C22.3098 9.93789 22.4526 9.22249 22.4526 8.5C22.4526 7.77751 22.3098 7.0621 22.0329 6.39464C21.756 5.72718 21.3508 5.12075 20.84 4.61Z"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'bell': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M18 8C18 6.4087 17.3679 4.88258 16.2426 3.75736C15.1174 2.63214 13.5913 2 12 2C10.4087 2 8.88258 2.63214 7.75736 3.75736C6.63214 4.88258 6 6.4087 6 8C6 15 3 17 3 17H21C21 17 18 15 18 8Z"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M13.73 21C13.5542 21.3031 13.3019 21.5547 12.9982 21.7295C12.6946 21.9044 12.3504 21.9965 12 21.9965C11.6496 21.9965 11.3054 21.9044 11.0018 21.7295C10.6982 21.5547 10.4458 21.3031 10.27 21"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </Svg>
    ),
    'xai-logo': (
      <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <Path
          d="M12 2L2 7V17L12 22L22 17V7L12 2Z"
          fill={iconColor}
          fillOpacity={0.2}
          stroke={iconColor}
          strokeWidth={2}
          strokeLinejoin="round"
        />
        <Path
          d="M8 10L12 14L16 10"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <Path
          d="M12 6V14"
          stroke={iconColor}
          strokeWidth={2}
          strokeLinecap="round"
        />
      </Svg>
    ),
  };

  return (
    <View style={style} accessibilityElementsHidden importantForAccessibility="no">
      {icons[name]}
    </View>
  );
}

export default Icon;
