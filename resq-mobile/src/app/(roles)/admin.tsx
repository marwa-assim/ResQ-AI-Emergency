import React, { useState, useEffect, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, SafeAreaView, Animated, ScrollView, TextInput } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { FontAwesome5 } from '@expo/vector-icons';
import { COLORS } from '../../constants/theme';
import axios from 'axios';
import { Platform } from 'react-native';

const SERVER_URL = Platform.OS === 'web' ? 'http://localhost:5000' : 'http://10.0.2.2:5000';

export default function AdminPortal() {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({ username: '', role: 'doctor', name: '' });
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }).start();
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
     try {
        const res = await axios.get(`${SERVER_URL}/api/admin/users`);
        setUsers(res.data.users);
     } catch(e){}
  };

  const createUser = async () => {
     try {
        await axios.post(`${SERVER_URL}/api/admin/users`, form);
        fetchUsers();
        setForm({ username: '', role: 'doctor', name: '' });
     } catch(e){}
  };

  return (
    <LinearGradient colors={['#1e293b', '#0f172a']} style={styles.container}>
       <SafeAreaView style={{flex: 1}}>
          <View style={styles.header}>
             <Text style={styles.brandTitle}><FontAwesome5 name="shield-alt" size={24} /> Admin Command</Text>
          </View>

          <ScrollView contentContainerStyle={styles.content}>
             <Animated.View style={{opacity: fadeAnim}}>
                <LinearGradient colors={['rgba(15,23,42,0.6)', 'rgba(15,23,42,0.8)']} style={styles.formCard}>
                   <Text style={styles.cardTitle}>Provision New User</Text>
                   
                   <Text style={styles.label}>Name</Text>
                   <TextInput style={styles.input} value={form.name} onChangeText={(t) => setForm({...form, name: t})} placeholderTextColor="#64748b" placeholder="Dr. John Doe" />
                   
                   <Text style={styles.label}>Username</Text>
                   <TextInput style={styles.input} value={form.username} onChangeText={(t) => setForm({...form, username: t})} placeholderTextColor="#64748b" placeholder="johndoe" autoCapitalize="none" />
                   
                   <Text style={styles.label}>Role</Text>
                   <View style={styles.roleGrid}>
                      {['doctor', 'nurse', 'ambulance', 'volunteer'].map(r => (
                         <TouchableOpacity key={r} style={[styles.roleBtn, form.role === r && styles.roleBtnActive]} onPress={() => setForm({...form, role: r})}>
                            <Text style={{color: form.role === r ? 'black' : 'white', fontWeight: 'bold', textTransform: 'capitalize'}}>{r}</Text>
                         </TouchableOpacity>
                      ))}
                   </View>

                   <TouchableOpacity style={styles.submitBtn} onPress={createUser}>
                      <Text style={{color: 'black', fontWeight: 'bold', fontSize: 16, textAlign: 'center'}}>CREATE USER</Text>
                   </TouchableOpacity>
                </LinearGradient>

                <Text style={[styles.cardTitle, {marginTop: 30, marginBottom: 15}]}>Directory ({users.length})</Text>
                {users.map((u:any, i) => (
                   <View key={i} style={styles.userRow}>
                      <View>
                         <Text style={{color: 'white', fontWeight: 'bold'}}>{u.name} <Text style={{color: COLORS.textSecondary, fontWeight: 'normal'}}>({u.username})</Text></Text>
                         <Text style={{color: COLORS.accentCyan, marginTop: 5, textTransform: 'uppercase', fontSize: 10}}>{u.role}</Text>
                      </View>
                      <TouchableOpacity style={styles.deleteBtn}>
                         <FontAwesome5 name="trash" color="#ef4444" />
                      </TouchableOpacity>
                   </View>
                ))}
             </Animated.View>
          </ScrollView>
       </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { padding: 20, borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.1)' },
  brandTitle: { color: '#facc15', fontSize: 24, fontWeight: '900', letterSpacing: 1 },
  content: { padding: 20 },
  formCard: { padding: 20, borderRadius: 16, borderWidth: 1, borderColor: 'rgba(250,204,21,0.3)' },
  cardTitle: { color: 'white', fontSize: 18, fontWeight: 'bold', marginBottom: 20 },
  label: { color: COLORS.textSecondary, marginBottom: 5 },
  input: { backgroundColor: 'rgba(0,0,0,0.3)', borderWidth: 1, borderColor: '#334155', borderRadius: 8, color: 'white', padding: 15, marginBottom: 15 },
  roleGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 20 },
  roleBtn: { backgroundColor: 'rgba(0,0,0,0.3)', borderWidth: 1, borderColor: '#334155', padding: 10, borderRadius: 8 },
  roleBtnActive: { backgroundColor: '#facc15', borderColor: '#facc15' },
  submitBtn: { backgroundColor: '#facc15', padding: 15, borderRadius: 8, marginTop: 10 },
  userRow: { backgroundColor: 'rgba(15,23,42,0.6)', padding: 15, borderRadius: 12, borderWidth: 1, borderColor: '#334155', marginBottom: 10, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  deleteBtn: { padding: 10 }
});
