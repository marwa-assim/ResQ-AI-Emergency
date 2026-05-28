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

export default function DoctorDashboard() {
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
               <Text style={styles.brandTitle}>ResQ AI</Text>
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
            <TouchableOpacity style={styles.chaosBtn}>
               <FontAwesome5 name="triangle-exclamation" size={14} color="white" />
               <Text style={{color: 'white', fontWeight: 'bold', marginLeft: 5}}>CHAOS</Text>
            </TouchableOpacity>
         </View>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
         <Animated.View style={{opacity: fadeAnim}}>
            {/* SMART CITY MAP */}
            <View style={styles.mapContainer}>
               <View style={{position: 'absolute', top: 15, left: 15, zIndex: 10}}>
                  <Text style={{color: '#94a3b8', fontSize: 12, fontWeight: 'bold', letterSpacing: 2}}>SMART CITY TRAFFIC GRID</Text>
                  <Text style={{color: '#475569', fontSize: 10}}>Live Feeds: <Text style={{color: '#22c55e'}}>ONLINE</Text></Text>
               </View>
               <View style={styles.droneContainer}>
                  <Text style={styles.droneTitle}>SKY-LINK FEED</Text>
               </View>
               <View style={styles.mapOverlay}>
                  <TouchableOpacity style={styles.dispatchBtn}>
                     <FontAwesome5 name="truck-medical" size={12} color="white" style={{marginRight: 5}} />
                     <Text style={{color: 'white', fontWeight: 'bold', fontSize: 12}}>DISPATCH</Text>
                  </TouchableOpacity>
                  <View style={styles.mapStat}><Text style={{color: '#aaa', fontSize: 12}}><FontAwesome5 name="car-side" /> Traffic: 84%</Text></View>
                  <View style={styles.mapStat}><Text style={{color: '#aaa', fontSize: 12}}><FontAwesome5 name="stopwatch" /> Delay: +2m</Text></View>
               </View>
            </View>

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

      {/* COMMAND PANEL TOGGLE */}
      <TouchableOpacity style={styles.cmdToggle} onPress={() => setShowCmd(!showCmd)}>
         <FontAwesome5 name="terminal" size={16} color={COLORS.accentCyan} />
         <Text style={{color: COLORS.accentCyan, marginLeft: 10, fontWeight: 'bold'}}>Command</Text>
      </TouchableOpacity>

      {/* COMMAND PANEL */}
      {showCmd && (
         <View style={styles.cmdPanel}>
            <View style={styles.macroDeck}>
               <View style={styles.macroGroup}>
                  <Text style={styles.macroGroupTitle}>ACTION</Text>
                  <View style={{flexDirection: 'row', gap: 5}}>
                     <TouchableOpacity style={[styles.macroBtn, {borderBottomColor: COLORS.accentCyan, borderBottomWidth: 2}]} onPress={() => setCmdText(cmdText + 'Discharge ')}><Text style={{color: 'white'}}>Discharge</Text></TouchableOpacity>
                     <TouchableOpacity style={[styles.macroBtn, {borderBottomColor: COLORS.accentCyan, borderBottomWidth: 2}]} onPress={() => setCmdText(cmdText + 'Note ')}><Text style={{color: 'white'}}>Note</Text></TouchableOpacity>
                  </View>
               </View>
               <View style={styles.macroGroup}>
                  <Text style={styles.macroGroupTitle}>TARGET BED</Text>
                  <View style={{flexDirection: 'row', gap: 5}}>
                     {[1,2,3,4].map(b => (
                        <TouchableOpacity key={b} style={[styles.macroBtn, {borderBottomColor: COLORS.riskHigh, borderBottomWidth: 2, minWidth: 40}]} onPress={() => setCmdText(cmdText + `Bed ${b} `)}><Text style={{color: 'white', textAlign: 'center'}}>{b}</Text></TouchableOpacity>
                     ))}
                  </View>
               </View>
            </View>
            <View style={styles.cmdInputRow}>
               <FontAwesome5 name="terminal" size={20} color={COLORS.accentCyan} />
               <TextInput style={styles.cmdInput} value={cmdText} onChangeText={setCmdText} placeholder="Type command..." placeholderTextColor="#64748b" />
               <TouchableOpacity><FontAwesome5 name="microphone" size={20} color="#94a3b8" /></TouchableOpacity>
            </View>
         </View>
      )}
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 20, borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.1)' },
  logoImg: { width: 50, height: 50 },
  brandTitle: { color: 'white', fontSize: 24, fontWeight: 'bold', textShadowColor: COLORS.accentCyan, textShadowRadius: 10 },
  brandSubtitle: { color: '#94a3b8', fontSize: 12 },
  headerStats: { flexDirection: 'row', alignItems: 'center' },
  chaosBtn: { flexDirection: 'row', alignItems: 'center', backgroundColor: COLORS.riskCritical, borderColor: 'white', borderWidth: 2, paddingHorizontal: 15, paddingVertical: 8, borderRadius: 8, marginLeft: 20 },
  scrollContent: { padding: 20, paddingBottom: 150 },
  mapContainer: { height: 250, backgroundColor: '#0f172a', borderRadius: 12, borderWidth: 1, borderColor: '#334155', shadowColor: 'black', shadowRadius: 20, marginBottom: 20, position: 'relative', overflow: 'hidden' },
  droneContainer: { position: 'absolute', top: 15, right: 15, width: 120, height: 90, backgroundColor: 'black', borderWidth: 2, borderColor: '#0284c7', borderRadius: 4, shadowColor: '#0284c7', shadowRadius: 10 },
  droneTitle: { backgroundColor: 'rgba(2,132,199,0.2)', padding: 2, color: 'white', fontSize: 8, fontWeight: 'bold' },
  mapOverlay: { position: 'absolute', bottom: 15, right: 15, flexDirection: 'row', gap: 10, alignItems: 'center' },
  dispatchBtn: { flexDirection: 'row', alignItems: 'center', backgroundColor: COLORS.riskCritical, borderColor: 'white', borderWidth: 1, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 4, shadowColor: COLORS.riskCritical, shadowRadius: 10 },
  mapStat: { backgroundColor: 'rgba(0,0,0,0.6)', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 4, borderWidth: 1, borderColor: '#333' },
  opsDeck: { flexDirection: width > 600 ? 'row' : 'column', gap: 20 },
  opsCol: { flex: 1 },
  opsTitle: { color: 'white', fontSize: 18, fontWeight: 'bold', marginBottom: 10, textShadowColor: COLORS.accentCyan, textShadowRadius: 10 },
  glassPanel: { borderRadius: 12, borderWidth: 1, borderColor: 'rgba(6,182,212,0.3)', padding: 15, minHeight: 200, shadowColor: COLORS.accentCyan, shadowRadius: 10 },
  queueItem: { backgroundColor: 'rgba(0,0,0,0.4)', padding: 10, borderRadius: 8, marginBottom: 10, flexDirection: 'row', justifyContent: 'space-between' },
  bedCard: { width: '45%', backgroundColor: 'rgba(0,0,0,0.4)', borderWidth: 1, padding: 10, borderRadius: 8, margin: '2.5%' },
  cmdToggle: { position: 'absolute', top: 20, right: 20, flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(59,130,246,0.2)', borderWidth: 1, borderColor: COLORS.accentCyan, padding: 10, borderRadius: 8 },
  cmdPanel: { position: 'absolute', bottom: 0, left: 0, width: '100%', backgroundColor: 'rgba(15,23,42,0.98)', borderTopWidth: 1, borderTopColor: COLORS.accentCyan, padding: 20, alignItems: 'center', shadowColor: 'black', shadowRadius: 20, shadowOffset: {width: 0, height: -5} },
  macroDeck: { flexDirection: 'row', gap: 30, marginBottom: 20 },
  macroGroup: { alignItems: 'center' },
  macroGroupTitle: { color: '#64748b', fontSize: 12, marginBottom: 10 },
  macroBtn: { backgroundColor: '#1e293b', borderColor: '#334155', borderWidth: 1, paddingHorizontal: 15, paddingVertical: 10, borderRadius: 6 },
  cmdInputRow: { width: '100%', maxWidth: 800, flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.3)', borderWidth: 1, borderColor: '#334155', borderRadius: 8, paddingHorizontal: 15, paddingVertical: 10, gap: 15 },
  cmdInput: { flex: 1, color: 'white', fontSize: 18, outlineStyle: 'none' }
});
