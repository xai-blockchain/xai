/**
 * Address Book Screen - Contact management
 *
 * Production-ready features:
 * - Save contacts with name and address
 * - Edit/delete contacts
 * - Quick select when sending
 * - Search contacts
 * - Favorite contacts
 * - Sort and filter options
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Alert,
  Modal,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import * as Clipboard from 'expo-clipboard';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { Card, Button, Input, Icon, EmptyState } from '../components';
import { useTheme } from '../theme';
import { triggerHaptic } from '../hooks/useHaptics';
import {
  getContacts,
  saveContact,
  updateContact,
  deleteContact,
  searchContacts,
} from '../utils/storage';
import { isValidAddress } from '../utils/crypto';
import { formatAddress } from '../utils/format';
import { spacing, borderRadius } from '../theme/spacing';
import { Contact, RootStackParamList } from '../types';

type AddressBookRouteProp = RouteProp<RootStackParamList, 'AddressBook'>;

type SortOption = 'name' | 'recent' | 'frequent';

interface ContactItemProps {
  contact: Contact;
  onPress: (contact: Contact) => void;
  onEdit: (contact: Contact) => void;
  onDelete: (contact: Contact) => void;
  onFavoriteToggle: (contact: Contact) => void;
  selectionMode?: boolean;
}

function ContactItem({
  contact,
  onPress,
  onEdit,
  onDelete,
  onFavoriteToggle,
  selectionMode = false,
}: ContactItemProps) {
  const theme = useTheme();

  return (
    <TouchableOpacity
      style={[styles.contactItem, { backgroundColor: theme.colors.surface }]}
      onPress={() => onPress(contact)}
      activeOpacity={0.7}
      accessibilityRole="button"
      accessibilityLabel={`${contact.name}, ${contact.address}`}
    >
      <View style={styles.contactMain}>
        {/* Avatar */}
        <View
          style={[
            styles.avatar,
            { backgroundColor: theme.colors.brand.primaryMuted },
          ]}
        >
          <Text style={[styles.avatarText, { color: theme.colors.brand.primary }]}>
            {contact.name.charAt(0).toUpperCase()}
          </Text>
        </View>

        {/* Info */}
        <View style={styles.contactInfo}>
          <View style={styles.contactNameRow}>
            <Text
              style={[styles.contactName, { color: theme.colors.text }]}
              numberOfLines={1}
            >
              {contact.name}
            </Text>
            {contact.isFavorite && (
              <Icon name="star" size={14} color={theme.colors.semantic.warning} />
            )}
          </View>
          <Text
            style={[styles.contactAddress, { color: theme.colors.textMuted }]}
            numberOfLines={1}
          >
            {formatAddress(contact.address, 10)}
          </Text>
          {contact.label && (
            <Text
              style={[styles.contactLabel, { color: theme.colors.textMuted }]}
              numberOfLines={1}
            >
              {contact.label}
            </Text>
          )}
        </View>
      </View>

      {/* Actions */}
      {!selectionMode && (
        <View style={styles.contactActions}>
          <TouchableOpacity
            onPress={() => onFavoriteToggle(contact)}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            accessibilityRole="button"
            accessibilityLabel={contact.isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            <Icon
              name={contact.isFavorite ? 'star' : 'star-outline'}
              size={20}
              color={
                contact.isFavorite
                  ? theme.colors.semantic.warning
                  : theme.colors.textMuted
              }
            />
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => onEdit(contact)}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            accessibilityRole="button"
            accessibilityLabel="Edit contact"
          >
            <Icon name="edit" size={20} color={theme.colors.textMuted} />
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => onDelete(contact)}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            accessibilityRole="button"
            accessibilityLabel="Delete contact"
          >
            <Icon name="trash" size={20} color={theme.colors.semantic.error} />
          </TouchableOpacity>
        </View>
      )}

      {selectionMode && (
        <Icon name="chevron-right" size={20} color={theme.colors.textMuted} />
      )}
    </TouchableOpacity>
  );
}

export function AddressBookScreen() {
  const theme = useTheme();
  const navigation = useNavigation();
  const route = useRoute<AddressBookRouteProp>();

  // Check if in selection mode (called from SendScreen)
  const selectionMode = route.params?.selectionMode || false;
  const onSelectContact = route.params?.onSelect;

  // State
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [filteredContacts, setFilteredContacts] = useState<Contact[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortOption>('name');
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [loading, setLoading] = useState(true);

  // Modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingContact, setEditingContact] = useState<Contact | null>(null);

  // Form state
  const [formName, setFormName] = useState('');
  const [formAddress, setFormAddress] = useState('');
  const [formLabel, setFormLabel] = useState('');
  const [formNotes, setFormNotes] = useState('');
  const [formErrors, setFormErrors] = useState<{ name?: string; address?: string }>({});
  const [saving, setSaving] = useState(false);

  // Load contacts
  const loadContacts = useCallback(async () => {
    try {
      const loaded = await getContacts();
      setContacts(loaded);
    } catch (error) {
      console.error('Failed to load contacts:', error);
      Alert.alert('Error', 'Failed to load contacts');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadContacts();
  }, [loadContacts]);

  // Filter and sort contacts
  useEffect(() => {
    let result = [...contacts];

    // Filter by favorites
    if (showFavoritesOnly) {
      result = result.filter((c) => c.isFavorite);
    }

    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (c) =>
          c.name.toLowerCase().includes(query) ||
          c.address.toLowerCase().includes(query) ||
          c.label?.toLowerCase().includes(query)
      );
    }

    // Sort
    switch (sortBy) {
      case 'name':
        result.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case 'recent':
        result.sort((a, b) => (b.lastUsed || b.createdAt) - (a.lastUsed || a.createdAt));
        break;
      case 'frequent':
        result.sort((a, b) => b.transactionCount - a.transactionCount);
        break;
    }

    // Favorites first
    result.sort((a, b) => (b.isFavorite ? 1 : 0) - (a.isFavorite ? 1 : 0));

    setFilteredContacts(result);
  }, [contacts, searchQuery, sortBy, showFavoritesOnly]);

  // Reset form
  const resetForm = useCallback(() => {
    setFormName('');
    setFormAddress('');
    setFormLabel('');
    setFormNotes('');
    setFormErrors({});
    setEditingContact(null);
  }, []);

  // Open add modal
  const handleOpenAdd = useCallback(
    (prefillAddress?: string) => {
      resetForm();
      if (prefillAddress) {
        setFormAddress(prefillAddress);
      }
      setShowAddModal(true);
    },
    [resetForm]
  );

  // Open edit modal
  const handleOpenEdit = useCallback((contact: Contact) => {
    setEditingContact(contact);
    setFormName(contact.name);
    setFormAddress(contact.address);
    setFormLabel(contact.label || '');
    setFormNotes(contact.notes || '');
    setFormErrors({});
    setShowAddModal(true);
  }, []);

  // Validate form
  const validateForm = useCallback(() => {
    const errors: { name?: string; address?: string } = {};

    if (!formName.trim()) {
      errors.name = 'Name is required';
    }

    if (!formAddress.trim()) {
      errors.address = 'Address is required';
    } else if (!isValidAddress(formAddress.trim())) {
      errors.address = 'Invalid XAI address format';
    }

    // Check for duplicate address (excluding current contact if editing)
    const existingContact = contacts.find(
      (c) =>
        c.address.toLowerCase() === formAddress.trim().toLowerCase() &&
        c.id !== editingContact?.id
    );
    if (existingContact) {
      errors.address = `Address already saved as "${existingContact.name}"`;
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }, [formName, formAddress, contacts, editingContact]);

  // Save contact
  const handleSave = useCallback(async () => {
    if (!validateForm()) return;

    setSaving(true);
    try {
      if (editingContact) {
        // Update existing
        await updateContact(editingContact.id, {
          name: formName.trim(),
          label: formLabel.trim() || undefined,
          notes: formNotes.trim() || undefined,
        });
        triggerHaptic('success');
      } else {
        // Create new
        await saveContact({
          name: formName.trim(),
          address: formAddress.trim(),
          label: formLabel.trim() || undefined,
          notes: formNotes.trim() || undefined,
          isFavorite: false,
        });
        triggerHaptic('success');
      }

      await loadContacts();
      setShowAddModal(false);
      resetForm();
    } catch (error) {
      console.error('Failed to save contact:', error);
      Alert.alert('Error', 'Failed to save contact');
    } finally {
      setSaving(false);
    }
  }, [
    validateForm,
    editingContact,
    formName,
    formAddress,
    formLabel,
    formNotes,
    loadContacts,
    resetForm,
  ]);

  // Delete contact
  const handleDelete = useCallback(
    (contact: Contact) => {
      Alert.alert('Delete Contact', `Are you sure you want to delete "${contact.name}"?`, [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteContact(contact.id);
              triggerHaptic('success');
              await loadContacts();
            } catch (error) {
              Alert.alert('Error', 'Failed to delete contact');
            }
          },
        },
      ]);
    },
    [loadContacts]
  );

  // Toggle favorite
  const handleFavoriteToggle = useCallback(
    async (contact: Contact) => {
      try {
        await updateContact(contact.id, { isFavorite: !contact.isFavorite });
        triggerHaptic('selection');
        await loadContacts();
      } catch (error) {
        Alert.alert('Error', 'Failed to update contact');
      }
    },
    [loadContacts]
  );

  // Handle contact press
  const handleContactPress = useCallback(
    (contact: Contact) => {
      if (selectionMode && onSelectContact) {
        onSelectContact(contact);
        navigation.goBack();
      } else {
        // Copy address
        Clipboard.setStringAsync(contact.address);
        triggerHaptic('success');
        Alert.alert('Copied', `${contact.name}'s address copied to clipboard`);
      }
    },
    [selectionMode, onSelectContact, navigation]
  );

  // Paste from clipboard
  const handlePasteAddress = useCallback(async () => {
    try {
      const text = await Clipboard.getStringAsync();
      if (text && isValidAddress(text.trim())) {
        setFormAddress(text.trim());
        triggerHaptic('selection');
      } else {
        Alert.alert('Invalid', 'Clipboard does not contain a valid XAI address');
      }
    } catch {
      Alert.alert('Error', 'Failed to read clipboard');
    }
  }, []);

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      {/* Search and filters */}
      <View style={styles.header}>
        <Input
          placeholder="Search contacts..."
          value={searchQuery}
          onChangeText={setSearchQuery}
          leftIcon="search"
          showClearButton
          onClear={() => setSearchQuery('')}
          containerStyle={styles.searchInput}
        />

        {/* Filter bar */}
        <View style={styles.filterBar}>
          <View style={styles.sortButtons}>
            {(['name', 'recent', 'frequent'] as SortOption[]).map((option) => (
              <TouchableOpacity
                key={option}
                style={[
                  styles.sortButton,
                  sortBy === option && { backgroundColor: theme.colors.brand.primaryMuted },
                ]}
                onPress={() => {
                  setSortBy(option);
                  triggerHaptic('selection');
                }}
              >
                <Text
                  style={[
                    styles.sortButtonText,
                    {
                      color:
                        sortBy === option
                          ? theme.colors.brand.primary
                          : theme.colors.textMuted,
                    },
                  ]}
                >
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <TouchableOpacity
            style={[
              styles.favoriteFilter,
              showFavoritesOnly && { backgroundColor: theme.colors.semantic.warningMuted },
            ]}
            onPress={() => {
              setShowFavoritesOnly(!showFavoritesOnly);
              triggerHaptic('selection');
            }}
          >
            <Icon
              name={showFavoritesOnly ? 'star' : 'star-outline'}
              size={18}
              color={
                showFavoritesOnly
                  ? theme.colors.semantic.warning
                  : theme.colors.textMuted
              }
            />
          </TouchableOpacity>
        </View>
      </View>

      {/* Contact list */}
      <FlatList
        data={filteredContacts}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <ContactItem
            contact={item}
            onPress={handleContactPress}
            onEdit={handleOpenEdit}
            onDelete={handleDelete}
            onFavoriteToggle={handleFavoriteToggle}
            selectionMode={selectionMode}
          />
        )}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          loading ? null : (
            <View style={styles.emptyContainer}>
              <Icon name="users" size={64} color={theme.colors.textMuted} />
              <Text style={[styles.emptyTitle, { color: theme.colors.text }]}>
                {searchQuery ? 'No contacts found' : 'No contacts yet'}
              </Text>
              <Text style={[styles.emptySubtitle, { color: theme.colors.textMuted }]}>
                {searchQuery
                  ? 'Try a different search term'
                  : 'Add contacts to quickly send XAI'}
              </Text>
              {!searchQuery && (
                <Button
                  title="Add Contact"
                  variant="primary"
                  onPress={() => handleOpenAdd()}
                  style={styles.emptyButton}
                />
              )}
            </View>
          )
        }
      />

      {/* Add button (FAB) */}
      {!selectionMode && (
        <TouchableOpacity
          style={[styles.fab, { backgroundColor: theme.colors.brand.primary }]}
          onPress={() => handleOpenAdd()}
          accessibilityRole="button"
          accessibilityLabel="Add contact"
        >
          <Icon name="plus" size={24} color="#ffffff" />
        </TouchableOpacity>
      )}

      {/* Add/Edit Modal */}
      <Modal
        visible={showAddModal}
        animationType="slide"
        transparent
        onRequestClose={() => {
          setShowAddModal(false);
          resetForm();
        }}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.modalContainer}
        >
          <View style={[styles.modalOverlay, { backgroundColor: theme.colors.overlay }]}>
            <View style={[styles.modalContent, { backgroundColor: theme.colors.surface }]}>
              {/* Modal Header */}
              <View
                style={[
                  styles.modalHeader,
                  { borderBottomColor: theme.colors.border },
                ]}
              >
                <Text style={[styles.modalTitle, { color: theme.colors.text }]}>
                  {editingContact ? 'Edit Contact' : 'Add Contact'}
                </Text>
                <Button
                  variant="ghost"
                  size="small"
                  onPress={() => {
                    setShowAddModal(false);
                    resetForm();
                  }}
                >
                  <Icon name="close" size={24} color={theme.colors.textMuted} />
                </Button>
              </View>

              {/* Form */}
              <View style={styles.form}>
                <Input
                  label="Name"
                  placeholder="Contact name"
                  value={formName}
                  onChangeText={(text) => {
                    setFormName(text);
                    setFormErrors((prev) => ({ ...prev, name: undefined }));
                  }}
                  error={formErrors.name}
                  autoFocus
                />

                <Input
                  label="Address"
                  placeholder="XAI..."
                  value={formAddress}
                  onChangeText={(text) => {
                    setFormAddress(text);
                    setFormErrors((prev) => ({ ...prev, address: undefined }));
                  }}
                  error={formErrors.address}
                  autoCapitalize="none"
                  autoCorrect={false}
                  editable={!editingContact}
                  rightElement={
                    !editingContact ? (
                      <Button
                        variant="ghost"
                        size="small"
                        onPress={handlePasteAddress}
                      >
                        <Text
                          style={[styles.pasteText, { color: theme.colors.brand.primary }]}
                        >
                          Paste
                        </Text>
                      </Button>
                    ) : undefined
                  }
                />

                <Input
                  label="Label (optional)"
                  placeholder="e.g., Work, Personal"
                  value={formLabel}
                  onChangeText={setFormLabel}
                />

                <Input
                  label="Notes (optional)"
                  placeholder="Any additional notes..."
                  value={formNotes}
                  onChangeText={setFormNotes}
                  multiline
                  numberOfLines={3}
                />

                {/* Save Button */}
                <Button
                  title={editingContact ? 'Save Changes' : 'Add Contact'}
                  variant="primary"
                  loading={saving}
                  onPress={handleSave}
                  style={styles.saveButton}
                />
              </View>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    padding: spacing['4'],
    paddingBottom: spacing['2'],
  },
  searchInput: {
    marginBottom: spacing['2'],
  },
  filterBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  sortButtons: {
    flexDirection: 'row',
    gap: spacing['2'],
  },
  sortButton: {
    paddingHorizontal: spacing['3'],
    paddingVertical: spacing['2'],
    borderRadius: borderRadius.md,
  },
  sortButtonText: {
    fontSize: 13,
    fontWeight: '500',
  },
  favoriteFilter: {
    padding: spacing['2'],
    borderRadius: borderRadius.md,
  },
  listContent: {
    padding: spacing['4'],
    paddingTop: spacing['2'],
  },
  // Contact item
  contactItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing['3'],
    borderRadius: borderRadius.lg,
    marginBottom: spacing['2'],
  },
  contactMain: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing['3'],
  },
  avatarText: {
    fontSize: 18,
    fontWeight: '600',
  },
  contactInfo: {
    flex: 1,
  },
  contactNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing['2'],
  },
  contactName: {
    fontSize: 16,
    fontWeight: '600',
  },
  contactAddress: {
    fontSize: 13,
    fontFamily: 'monospace',
    marginTop: 2,
  },
  contactLabel: {
    fontSize: 12,
    marginTop: 2,
  },
  contactActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing['4'],
    marginLeft: spacing['3'],
  },
  // Empty state
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: spacing['8'],
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginTop: spacing['4'],
  },
  emptySubtitle: {
    fontSize: 14,
    marginTop: spacing['2'],
    textAlign: 'center',
  },
  emptyButton: {
    marginTop: spacing['6'],
  },
  // FAB
  fab: {
    position: 'absolute',
    right: spacing['4'],
    bottom: spacing['4'],
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  // Modal
  modalContainer: {
    flex: 1,
  },
  modalOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  modalContent: {
    borderTopLeftRadius: borderRadius.xl,
    borderTopRightRadius: borderRadius.xl,
    maxHeight: '90%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing['4'],
    borderBottomWidth: 1,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  form: {
    padding: spacing['4'],
  },
  pasteText: {
    fontSize: 14,
    fontWeight: '600',
  },
  saveButton: {
    marginTop: spacing['4'],
  },
});
