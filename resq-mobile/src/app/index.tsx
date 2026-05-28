import React, { useRef, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, SafeAreaView, Animated, Image, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { FontAwesome5 } from '@expo/vector-icons';
import { router } from 'expo-router';
import { COLORS } from '../constants/theme';

export default function Index() {
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 1000, useNativeDriver: true }).start();
  }, []);

  const roles = [
    { id: 'patient', name: 'Patient / Volunteer SOS', icon: 'user-injured', color: COLORS.accentCyan },
    { id: 'ambulance', name: 'Ambulance Portal', icon: 'ambulance', color: COLORS.riskCritical },
    { id: 'doctor', name: 'Doctor Dashboard', icon: 'stethoscope', color: COLORS.riskHigh },
    { id: 'nurse', name: 'ER Nurse Portal', icon: 'user-nurse', color: COLORS.accentMagenta },
    { id: 'admin', name: 'Global Command (Admin)', icon: 'shield-alt', color: '#facc15' }
  ];

  return (
    <LinearGradient colors={['#1e293b', '#0f172a']} style={styles.container}>
      <SafeAreaView style={{flex: 1}}>
        <Animated.View style={[styles.content, { opacity: fadeAnim }]}>
           <View style={styles.header}>
              <Image source={{uri: `http://localhost:5000/static/ResQ%20AI%20Logo.png`}} style={styles.logoImg} resizeMode="contain" />
              <Text style={styles.brandTitle}>ResQ Connect</Text>
              <Text style={styles.brandSubtitle}>Mobile Portal Selection</Text>
           </View>
           
           <View style={styles.grid}>
              {roles.map((r, i) => (
                 <TouchableOpacity key={i} style={styles.roleBtn} onPress={() => router.push(`/(roles)/${r.id}` as any)}>
                    <View style={[styles.iconBox, {backgroundColor: 'rgba(255,255,255,0.1)'}]}>
                       <FontAwesome5 name={r.icon} size={24} color={r.color} />
                    </View>
                    <Text style={styles.roleName}>{r.name}</Text>
                    <FontAwesome5 name="chevron-right" size={16} color="#64748b" style={{marginLeft: 'auto'}} />
                 </TouchableOpacity>
              ))}
           </View>
        </Animated.View>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { flex: 1, padding: 20, justifyContent: 'center', alignItems: 'center' },
  header: { alignItems: 'center', marginBottom: 40 },
  logoImg: { width: 200, height: 100, marginBottom: 10 },
  brandTitle: { color: 'white', fontSize: 32, fontWeight: 'bold' },
  brandSubtitle: { color: '#94a3b8', fontSize: 16 },
  grid: { width: '100%', maxWidth: 500 },
  roleBtn: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(15,23,42,0.6)', padding: 20, borderRadius: 20, marginBottom: 15, borderWidth: 1, borderColor: 'rgba(6,182,212,0.3)' },
  iconBox: { width: 50, height: 50, borderRadius: 12, alignItems: 'center', justifyContent: 'center', marginRight: 15 },
  roleName: { color: 'white', fontSize: 18, fontWeight: 'bold' }
});
