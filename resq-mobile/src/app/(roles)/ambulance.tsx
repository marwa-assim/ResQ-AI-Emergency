import React, { useState, useEffect, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, SafeAreaView, Animated, Dimensions, Platform, Image } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { FontAwesome5 } from '@expo/vector-icons';
import { COLORS } from '../../constants/theme';
import axios from 'axios';
import { io } from 'socket.io-client';

const SERVER_URL = Platform.OS === 'web' ? 'http://localhost:5000' : 'http://10.0.2.2:5000';
const AMBULANCE_ID = "AMB-ALPHA-1";

export default function AmbulancePortal() {
  const [status, setStatus] = useState('IDLE');
  const [mission, setMission] = useState<any>(null);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }).start();
    
    const socket = io(SERVER_URL);
    socket.emit('register_ambulance', { id: AMBULANCE_ID });
    
    socket.on('dispatch_ambulance', (data) => {
       setMission(data);
       setStatus('NAV_PATIENT');
    });
    
    return () => socket.disconnect();
  }, []);

  const updateStatus = async (newStatus: string) => {
     setStatus(newStatus);
     try {
        await axios.post(`${SERVER_URL}/api/ambulance/update`, { id: AMBULANCE_ID, status: newStatus });
     } catch(e){}
  };

  const renderStateContent = () => {
     if (status === 'IDLE') return (
        <View style={styles.centerBox}>
           <FontAwesome5 name="coffee" size={50} color={COLORS.textSecondary} style={{marginBottom: 20}} />
           <Text style={styles.idleTitle}>Awaiting Dispatch</Text>
           <Text style={{color: COLORS.textSecondary}}>Monitoring emergency frequencies...</Text>
        </View>
     );

     if (status === 'NAV_PATIENT') return (
        <View style={styles.activeMission}>
           <Text style={styles.missionTitle}>⚠️ EMERGENCY DISPATCH</Text>
           <View style={styles.dataRow}><Text style={{color: '#94a3b8'}}>Destination:</Text><Text style={{color: 'white', fontWeight: 'bold'}}>{mission?.location || 'Downtown Sector 4'}</Text></View>
           <View style={styles.dataRow}><Text style={{color: '#94a3b8'}}>Notes:</Text><Text style={{color: 'white', fontWeight: 'bold'}}>{mission?.notes || 'Unknown Emergency'}</Text></View>
           <TouchableOpacity style={styles.actionBtn} onPress={() => updateStatus('ON_SCENE')}>
              <Text style={styles.actionBtnTxt}>ARRIVED ON SCENE</Text>
           </TouchableOpacity>
        </View>
     );

     if (status === 'ON_SCENE') return (
        <View style={styles.activeMission}>
           <Text style={[styles.missionTitle, {color: COLORS.riskHigh}]}>🚑 PATIENT STABILIZATION</Text>
           <Text style={{color: 'white', marginBottom: 20}}>Administering first aid and securing patient.</Text>
           <TouchableOpacity style={[styles.actionBtn, {backgroundColor: COLORS.riskHigh}]} onPress={() => updateStatus('NAV_HOSPITAL')}>
              <Text style={[styles.actionBtnTxt, {color: 'black'}]}>BEGIN TRANSPORT</Text>
           </TouchableOpacity>
        </View>
     );

     if (status === 'NAV_HOSPITAL') return (
        <View style={styles.activeMission}>
           <Text style={[styles.missionTitle, {color: COLORS.accentCyan}]}>🏥 TRANSPORTING TO RESQ HOSPITAL</Text>
           <TouchableOpacity style={[styles.actionBtn, {backgroundColor: COLORS.accentCyan}]} onPress={() => updateStatus('IDLE')}>
              <Text style={[styles.actionBtnTxt, {color: 'black'}]}>PATIENT DELIVERED</Text>
           </TouchableOpacity>
        </View>
     );
  };

  return (
    <LinearGradient colors={['#1e293b', '#0f172a']} style={styles.container}>
       <SafeAreaView style={{flex: 1}}>
          <View style={styles.header}>
             <Text style={styles.brandTitle}>MDT SYSTEM</Text>
             <View style={styles.statusBadge}><Text style={{color: 'black', fontWeight: 'bold'}}>{AMBULANCE_ID}</Text></View>
          </View>

          <Animated.View style={[styles.content, {opacity: fadeAnim}]}>
             {/* MAP PLACEHOLDER */}
             <View style={styles.mapContainer}>
                <View style={{position: 'absolute', top: 10, left: 10, zIndex: 1}}>
                   <Text style={{color: 'white', fontWeight: 'bold', fontSize: 18}}>GPS NAVLINK</Text>
                </View>
             </View>
             
             {/* STATE CONTENT */}
             {renderStateContent()}
          </Animated.View>
       </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { padding: 20, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.1)' },
  brandTitle: { color: COLORS.riskCritical, fontSize: 24, fontWeight: '900', letterSpacing: 2 },
  statusBadge: { backgroundColor: COLORS.riskLow, paddingHorizontal: 15, paddingVertical: 5, borderRadius: 20 },
  content: { flex: 1, padding: 20 },
  mapContainer: { height: 250, backgroundColor: '#0f172a', borderRadius: 12, borderWidth: 1, borderColor: '#334155', marginBottom: 20 },
  centerBox: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.4)', borderRadius: 12, borderWidth: 1, borderColor: '#334155' },
  idleTitle: { color: 'white', fontSize: 24, fontWeight: 'bold', marginBottom: 10 },
  activeMission: { backgroundColor: 'rgba(0,0,0,0.4)', padding: 20, borderRadius: 12, borderWidth: 1, borderColor: COLORS.riskCritical },
  missionTitle: { color: COLORS.riskCritical, fontSize: 20, fontWeight: 'bold', marginBottom: 20 },
  dataRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#334155' },
  actionBtn: { backgroundColor: COLORS.riskCritical, padding: 20, borderRadius: 12, alignItems: 'center', marginTop: 30 },
  actionBtnTxt: { color: 'white', fontWeight: 'bold', fontSize: 18 }
});
