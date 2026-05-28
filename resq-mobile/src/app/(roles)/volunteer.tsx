import React, { useState, useEffect, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, SafeAreaView, Animated, ScrollView, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { FontAwesome5 } from '@expo/vector-icons';
import { COLORS } from '../../constants/theme';

const { width } = Dimensions.get('window');

export default function VolunteerPortal() {
  const [missions, setMissions] = useState([
     { id: 1, title: 'CPR Required', distance: '0.2 miles', type: 'critical' },
     { id: 2, title: 'First Aid - Bleeding', distance: '0.5 miles', type: 'high' }
  ]);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }).start();
  }, []);

  return (
    <LinearGradient colors={['#1e293b', '#0f172a']} style={styles.container}>
       <SafeAreaView style={{flex: 1}}>
          <View style={styles.header}>
             <Text style={styles.brandTitle}><FontAwesome5 name="hands-helping" size={24} /> Volunteer Network</Text>
             <View style={styles.statusBadge}><View style={styles.statusDot}/><Text style={{color: '#22c55e', fontWeight: 'bold'}}>ON DUTY</Text></View>
          </View>

          <ScrollView contentContainerStyle={styles.content}>
             <Animated.View style={{opacity: fadeAnim}}>
                <View style={styles.mapContainer}>
                   <View style={{position: 'absolute', top: 10, left: 10, zIndex: 1}}>
                      <Text style={{color: 'white', fontWeight: 'bold', fontSize: 18}}>RADAR SCAN ACTIVE</Text>
                   </View>
                </View>

                <Text style={styles.sectionTitle}>Nearby Emergencies</Text>
                {missions.map(m => (
                   <TouchableOpacity key={m.id} style={[styles.missionCard, m.type === 'critical' ? {borderColor: COLORS.riskCritical} : {borderColor: COLORS.riskHigh}]}>
                      <View style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'}}>
                         <View>
                            <Text style={styles.missionTitle}>{m.title}</Text>
                            <Text style={{color: '#94a3b8'}}><FontAwesome5 name="map-marker-alt" /> {m.distance} away</Text>
                         </View>
                         <View style={[styles.acceptBtn, m.type === 'critical' ? {backgroundColor: COLORS.riskCritical} : {backgroundColor: COLORS.riskHigh}]}>
                            <Text style={{color: 'white', fontWeight: 'bold'}}>ACCEPT</Text>
                         </View>
                      </View>
                   </TouchableOpacity>
                ))}
             </Animated.View>
          </ScrollView>
       </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { padding: 20, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.1)' },
  brandTitle: { color: COLORS.accentCyan, fontSize: 24, fontWeight: '900', letterSpacing: 1 },
  statusBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(34,197,94,0.2)', paddingHorizontal: 15, paddingVertical: 5, borderRadius: 20, borderWidth: 1, borderColor: '#22c55e' },
  statusDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#22c55e', marginRight: 5 },
  content: { padding: 20 },
  mapContainer: { height: 250, backgroundColor: '#0f172a', borderRadius: 12, borderWidth: 1, borderColor: '#334155', marginBottom: 20 },
  sectionTitle: { color: 'white', fontSize: 20, fontWeight: 'bold', marginBottom: 15 },
  missionCard: { backgroundColor: 'rgba(15,23,42,0.6)', padding: 20, borderRadius: 12, borderWidth: 1, marginBottom: 15 },
  missionTitle: { color: 'white', fontSize: 18, fontWeight: 'bold', marginBottom: 5 },
  acceptBtn: { paddingHorizontal: 20, paddingVertical: 10, borderRadius: 8 }
});
