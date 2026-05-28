import React, { useState, useEffect, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Animated, Image, TextInput, Platform, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { FontAwesome5 } from '@expo/vector-icons';
import { router } from 'expo-router';
import axios from 'axios';
import { io } from 'socket.io-client';
import { COLORS } from '../../constants/theme';

const SERVER_URL = Platform.OS === 'web' ? 'http://localhost:5000' : 'http://10.0.2.2:5000';
const { width } = Dimensions.get('window');

export default function NurseDashboard() {
  const [patients, setPatients] = useState([]);
  const [beds, setBeds] = useState([]);
  const [showCmd, setShowCmd] = useState(false);
  const [cmdText, setCmdText] = useState('');

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const logoRotateAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }).start();
    Animated.loop(
      Animated.sequence([
         Animated.timing(logoRotateAnim, { toValue: 1, duration: 3000, useNativeDriver: true }),
         Animated.timing(logoRotateAnim, { toValue: -1, duration: 3000, useNativeDriver: true })
      ])
    ).start();
    
    fetchData();
    const socket = io(SERVER_URL);
    socket.on('queue_update', () => fetchData());
    socket.on('vital_update', () => fetchData());
    return () => socket.disconnect();
  }, []);

  const fetchData = async () => {
     try {
        const qRes = await axios.get(`${SERVER_URL}/api/queue`);
        setPatients(qRes.data || []);
        const bRes = await axios.get(`${SERVER_URL}/api/beds`);
        setBeds(bRes.data || []);
     } catch (e) { console.log('Fetch error'); }
  };

  const logoSpin = logoRotateAnim.interpolate({
      inputRange: [-1, 1],
      outputRange: ['-15deg', '15deg']
  });

  return (
    <LinearGradient colors={['#1e293b', '#0f172a']} style={styles.container}>
      {/* HEADER */}
      <View style={styles.header}>
         <View style={{flexDirection: 'row', alignItems: 'center', gap: 10}}>
            <Animated.Image source={{uri: `${SERVER_URL}/static/ResQ%20AI%20Logo.png`}} style={[styles.logoImg, {transform: [{rotateY: logoSpin}]}]} />
            <View>
               <Text style={styles.brandTitle}>ER Nurse</Text>
               <Text style={styles.brandSubtitle}>Command Center</Text>
            </View>
         </View>
         
         <View style={styles.headerStats}>
            <View style={{alignItems: 'flex-end'}}>
               <Text style={{color: COLORS.textSecondary, fontSize: 12}}>Waiting</Text>
               <Text style={{color: COLORS.riskHigh, fontSize: 24, fontWeight: 'bold'}}>{patients.length}</Text>
            </View>
            <View style={{alignItems: 'flex-end', marginLeft: 20}}>
               <Text style={{color: COLORS.textSecondary, fontSize: 12}}>Beds Free</Text>
               <Text style={{color: COLORS.riskLow, fontSize: 24, fontWeight: 'bold'}}>{beds.filter((b:any)=>!b.occupied).length}</Text>
            </View>
         </View>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
         <Animated.View style={{opacity: fadeAnim}}>
            {/* OPS DECK */}
            <View style={styles.opsDeck}>
               <View style={styles.opsCol}>
                  <Text style={styles.opsTitle}>Waiting Queue</Text>
                  <LinearGradient colors={['rgba(15,23,42,0.6)', 'rgba(15,23,42,0.8)']} style={styles.glassPanel}>
                     {patients.map((p:any, i) => (
                        <View key={i} style={styles.queueItem}>
                           <Text style={{color: 'white', fontWeight: 'bold'}}>{p.name || 'Unknown'}</Text>
                           <Text style={{color: COLORS.riskHigh}}>{p.triage_risk}</Text>
                        </View>
                     ))}
                     {patients.length === 0 && <Text style={{color: '#64748b', padding: 20, textAlign: 'center'}}>No patients waiting</Text>}
                  </LinearGradient>
               </View>

               <View style={[styles.opsCol, {flex: 1.5}]}>
                  <Text style={styles.opsTitle}>ER Treatment Area</Text>
                  <LinearGradient colors={['rgba(15,23,42,0.6)', 'rgba(15,23,42,0.8)']} style={[styles.glassPanel, {flexDirection: 'row', flexWrap: 'wrap'}]}>
                     {beds.map((b:any, i) => (
                        <View key={i} style={[styles.bedCard, {borderColor: b.occupied ? COLORS.riskHigh : COLORS.border}]}>
                           <Text style={{color: 'white', fontWeight: 'bold'}}>Bed {b.id}</Text>
                           <Text style={{color: b.occupied ? COLORS.riskHigh : COLORS.riskLow, fontSize: 12}}>{b.occupied ? b.patient?.name : 'AVAILABLE'}</Text>
                        </View>
                     ))}
                  </LinearGradient>
               </View>
            </View>
         </Animated.View>
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 20, borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.1)' },
  logoImg: { width: 50, height: 50 },
  brandTitle: { color: COLORS.accentMagenta, fontSize: 24, fontWeight: 'bold', textShadowColor: COLORS.accentMagenta, textShadowRadius: 10 },
  brandSubtitle: { color: '#94a3b8', fontSize: 12 },
  headerStats: { flexDirection: 'row', alignItems: 'center' },
  scrollContent: { padding: 20, paddingBottom: 150 },
  opsDeck: { flexDirection: width > 600 ? 'row' : 'column', gap: 20 },
  opsCol: { flex: 1 },
  opsTitle: { color: 'white', fontSize: 18, fontWeight: 'bold', marginBottom: 10, textShadowColor: COLORS.accentCyan, textShadowRadius: 10 },
  glassPanel: { borderRadius: 12, borderWidth: 1, borderColor: 'rgba(6,182,212,0.3)', padding: 15, minHeight: 200, shadowColor: COLORS.accentCyan, shadowRadius: 10 },
  queueItem: { backgroundColor: 'rgba(0,0,0,0.4)', padding: 10, borderRadius: 8, marginBottom: 10, flexDirection: 'row', justifyContent: 'space-between' },
  bedCard: { width: '45%', backgroundColor: 'rgba(0,0,0,0.4)', borderWidth: 1, padding: 10, borderRadius: 8, margin: '2.5%' },
});
