import React, { useState, useEffect, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Animated, Image, TextInput, Platform, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { FontAwesome5 } from '@expo/vector-icons';
import { router } from 'expo-router';
import * as Speech from 'expo-speech';
import axios from 'axios';
import { COLORS } from '../../constants/theme';

const SERVER_URL = Platform.OS === 'web' ? 'http://localhost:5000' : 'http://10.0.2.2:5000';
const { width } = Dimensions.get('window');

export default function PatientPortal() {
  const [message, setMessage] = useState('');
  const [blindMode, setBlindMode] = useState(false);
  const [chatLog, setChatLog] = useState([
    { sender: 'ai', text: "Hi! I'm Nurse Sara, your AI medical assistant. Tap a quick-action below or type any medical question - I'll guide you step by step. 🩺" }
  ]);

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const floatAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }).start();
    
    Animated.loop(
      Animated.sequence([
        Animated.timing(floatAnim, { toValue: -10, duration: 2000, useNativeDriver: true }),
        Animated.timing(floatAnim, { toValue: 0, duration: 2000, useNativeDriver: true })
      ])
    ).start();

    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.05, duration: 1500, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 1500, useNativeDriver: true })
      ])
    ).start();
  }, []);

  const speak = (text: string) => {
     if (blindMode) {
        Speech.stop();
        Speech.speak(text);
     }
  };

  const toggleBlindMode = () => {
     const newMode = !blindMode;
     setBlindMode(newMode);
     if (newMode) {
        Speech.speak("Vision Impaired Mode Active. I will read the screen buttons for you.");
     } else {
        Speech.speak("Voice Guidance Deactivated.");
     }
  };

  const handleSend = () => {
    if (!message) return;
    speak("Message sent: " + message);
    setChatLog(prev => [...prev, { sender: 'user', text: message }]);
    setTimeout(() => {
        const response = "I have received your message. Activating triage protocols.";
        setChatLog(prev => [...prev, { sender: 'ai', text: response }]);
        speak(response);
    }, 1000);
    setMessage('');
  };

  return (
    <LinearGradient colors={['#1e293b', '#0f172a']} style={styles.container}>
      {/* Fixed Access Overlay */}
      <View style={styles.fixedAccess}>
         <TouchableOpacity 
            style={[styles.floatingBtn, blindMode && {backgroundColor: '#22c55e', borderColor: '#22c55e'}]} 
            onPress={toggleBlindMode}
            accessibilityLabel="Toggle Blind Mode"
         >
            <FontAwesome5 name="eye-slash" size={20} color="white" />
         </TouchableOpacity>
         <TouchableOpacity style={styles.floatingBtn} onPress={() => speak("Microphone Mode currently unavailable in this build.")}>
            <FontAwesome5 name="microphone" size={20} color="white" />
         </TouchableOpacity>
         <TouchableOpacity 
            style={[styles.floatingBtn, {backgroundColor: 'rgba(56,189,248,0.12)', borderColor: '#38bdf8'}]} 
            onPress={() => {
               speak("Opening Sign Language Mode");
               router.push('/(roles)/sign_language');
            }}
         >
            <Text style={{fontSize: 24}}>🤟</Text>
         </TouchableOpacity>
      </View>

      {/* SOS BAR */}
      <View style={styles.sosBar}>
         <Animated.View style={{transform: [{scale: pulseAnim}]}}>
            <TouchableOpacity style={styles.btnPanic} onPress={() => speak("Dialing 9 1 1.")}>
               <FontAwesome5 name="phone" size={16} color="white" style={{marginRight: 8}} />
               <Text style={styles.btnPanicTxt}>CALL 911</Text>
            </TouchableOpacity>
         </Animated.View>
         <TouchableOpacity style={styles.btnDispatch} onPress={() => speak("Ambulance Dispatched to your location.")}>
            <FontAwesome5 name="truck-medical" size={16} color="#ef4444" style={{marginRight: 8}} />
            <Text style={styles.btnDispatchTxt}>SEND AMBULANCE</Text>
         </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
         <Animated.View style={{opacity: fadeAnim}}>
            {/* Header Logo */}
            <View style={styles.header}>
               <Image source={{uri: `${SERVER_URL}/static/ResQ%20AI%20Logo.png`}} style={styles.logoImg} resizeMode="contain" />
               <Text style={styles.brandTitle}>ResQ Connect</Text>
               <Text style={styles.brandSubtitle}>Pre-Hospital Emergency Portal</Text>
            </View>

            {/* AI Assistant Box */}
            <LinearGradient colors={['rgba(6, 182, 212, 0.15)', 'rgba(15, 23, 42, 0.9)']} style={styles.aiBox}>
               <Animated.Image source={{uri: `${SERVER_URL}/static/ai_nurse.png`}} style={[styles.aiAvatar, { transform: [{translateY: floatAnim}] }]} />
               <Text style={styles.aiTitle}>Hi, I'm Nurse Sara.</Text>
               <Text style={styles.aiSubtitle}>I'm here to guide you. Tell me what's happening.</Text>

               {/* Chat Log */}
               <View style={styles.chatLog}>
                  {chatLog.map((c, i) => (
                     <View key={i} style={[styles.chatRow, c.sender === 'user' ? {justifyContent: 'flex-end'} : {}]}>
                        {c.sender === 'ai' && <View style={styles.aiAvatarSmall}><Text>👩‍⚕️</Text></View>}
                        <LinearGradient colors={c.sender === 'user' ? ['#0f172a', '#1e293b'] : ['rgba(6,182,212,0.18)', 'rgba(2,132,199,0.12)']} style={styles.chatBubble}>
                           <Text style={styles.chatTxt}>{c.text}</Text>
                        </LinearGradient>
                     </View>
                  ))}
               </View>

               {/* Chips */}
               <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipsScroll}>
                  <TouchableOpacity style={[styles.chip, {borderColor: 'rgba(239,68,68,.5)', backgroundColor: 'rgba(239,68,68,.12)'}]} onPress={() => {speak("Selected Bleeding"); setMessage('Bleeding');}}><Text style={{color: '#fca5a5'}}>🩸 Bleeding</Text></TouchableOpacity>
                  <TouchableOpacity style={[styles.chip, {borderColor: 'rgba(6,182,212,.5)', backgroundColor: 'rgba(6,182,212,.12)'}]} onPress={() => {speak("Selected CPR"); setMessage('CPR needed');}}><Text style={{color: '#67e8f9'}}>🫀 CPR</Text></TouchableOpacity>
                  <TouchableOpacity style={[styles.chip, {borderColor: 'rgba(251,191,36,.5)', backgroundColor: 'rgba(251,191,36,.12)'}]} onPress={() => {speak("Selected Choking"); setMessage('Choking');}}><Text style={{color: '#fde68a'}}>😮 Choking</Text></TouchableOpacity>
                  <TouchableOpacity style={[styles.chip, {borderColor: 'rgba(249,115,22,.5)', backgroundColor: 'rgba(249,115,22,.12)'}]} onPress={() => {speak("Selected Burns"); setMessage('Burns');}}><Text style={{color: '#fdba74'}}>🔥 Burns</Text></TouchableOpacity>
               </ScrollView>

               {/* Input Row */}
               <View style={styles.inputRow}>
                  <TextInput style={styles.input} placeholder="Ask any medical question..." placeholderTextColor="#94a3b8" value={message} onChangeText={setMessage} onSubmitEditing={handleSend} />
                  <TouchableOpacity style={styles.micBtn} onPress={() => speak("Microphone Mode currently unavailable in this build.")}><FontAwesome5 name="microphone" size={20} color={COLORS.accentCyan} /></TouchableOpacity>
                  <TouchableOpacity style={styles.slBtn} onPress={() => {
                     speak("Opening Sign Language Mode");
                     router.push('/(roles)/sign_language');
                  }}><Text style={{fontSize: 20}}>🤟</Text></TouchableOpacity>
               </View>
            </LinearGradient>

            {/* Check-In Cards */}
            <Text style={styles.sectionTitle}>Start Self-Check In</Text>
            <TouchableOpacity style={styles.cardBtn} onPress={() => speak("Self check in for Chest Pain")}>
               <View style={styles.cardRow}>
                  <View style={[styles.iconBox, {color: COLORS.riskCritical}]}><FontAwesome5 name="heartbeat" size={24} color={COLORS.riskCritical} /></View>
                  <View style={styles.cardTextContainer}>
                     <Text style={styles.cardTitle}>Chest Pain</Text>
                     <Text style={styles.cardDesc}>Pressure, tightness, heart issues</Text>
                  </View>
               </View>
               <FontAwesome5 name="chevron-right" size={16} color="#64748b" />
            </TouchableOpacity>

            <TouchableOpacity style={styles.cardBtn} onPress={() => speak("Self check in for Trouble Breathing")}>
               <View style={styles.cardRow}>
                  <View style={[styles.iconBox, {color: COLORS.riskHigh}]}><FontAwesome5 name="lungs" size={24} color={COLORS.riskHigh} /></View>
                  <View style={styles.cardTextContainer}>
                     <Text style={styles.cardTitle}>Trouble Breathing</Text>
                     <Text style={styles.cardDesc}>Shortness of breath, asthma</Text>
                  </View>
               </View>
               <FontAwesome5 name="chevron-right" size={16} color="#64748b" />
            </TouchableOpacity>

         </Animated.View>
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  fixedAccess: { position: 'absolute', top: 90, right: 20, zIndex: 2000, gap: 15 },
  floatingBtn: { width: 60, height: 60, borderRadius: 30, backgroundColor: 'rgba(15,23,42,0.8)', borderWidth: 2, borderColor: COLORS.accentCyan, alignItems: 'center', justifyContent: 'center', shadowColor: COLORS.accentCyan, shadowOpacity: 0.4, shadowRadius: 15 },
  sosBar: { backgroundColor: 'rgba(69,10,10,0.9)', borderBottomWidth: 3, borderBottomColor: '#ef4444', padding: 15, flexDirection: 'row', justifyContent: 'center', gap: 15, zIndex: 100 },
  btnPanic: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#dc2626', paddingVertical: 12, paddingHorizontal: 25, borderRadius: 50 },
  btnPanicTxt: { color: 'white', fontWeight: 'bold', fontSize: 16 },
  btnDispatch: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.3)', borderWidth: 2, borderColor: '#ef4444', paddingVertical: 12, paddingHorizontal: 20, borderRadius: 50 },
  btnDispatchTxt: { color: '#ef4444', fontWeight: 'bold' },
  scrollContent: { padding: 20, paddingBottom: 100 },
  header: { alignItems: 'center', marginBottom: 30 },
  logoImg: { width: 200, height: 100, marginBottom: 10 },
  brandTitle: { color: 'white', fontSize: 32, fontWeight: 'bold' },
  brandSubtitle: { color: '#94a3b8', fontSize: 16 },
  aiBox: { borderRadius: 24, borderWidth: 1, borderColor: 'rgba(6,182,212,0.4)', padding: 20, marginBottom: 30, alignItems: 'center' },
  aiAvatar: { width: 120, height: 120, borderRadius: 60, borderWidth: 4, borderColor: COLORS.accentCyan, marginBottom: 20 },
  aiTitle: { color: 'white', fontSize: 24, fontWeight: 'bold', marginBottom: 5 },
  aiSubtitle: { color: '#94a3b8', fontSize: 16, textAlign: 'center', marginBottom: 20 },
  chatLog: { width: '100%', maxHeight: 200, backgroundColor: 'rgba(0,0,0,0.25)', borderRadius: 12, padding: 12, borderWidth: 1, borderColor: 'rgba(255,255,255,0.06)', marginBottom: 15 },
  chatRow: { flexDirection: 'row', marginBottom: 10 },
  aiAvatarSmall: { width: 30, height: 30, borderRadius: 15, backgroundColor: '#0284c7', alignItems: 'center', justifyContent: 'center', marginRight: 10 },
  chatBubble: { maxWidth: '82%', padding: 10, borderRadius: 14, borderWidth: 1, borderColor: 'rgba(6,182,212,0.3)' },
  chatTxt: { color: '#e2e8f0', fontSize: 14, lineHeight: 20 },
  chipsScroll: { flexDirection: 'row', marginBottom: 15 },
  chip: { paddingVertical: 8, paddingHorizontal: 15, borderRadius: 20, borderWidth: 1, marginRight: 10 },
  inputRow: { flexDirection: 'row', width: '100%', position: 'relative' },
  input: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', borderWidth: 2, borderColor: 'rgba(255,255,255,0.15)', borderRadius: 60, color: 'white', padding: 15, paddingRight: 90, fontSize: 16 },
  micBtn: { position: 'absolute', right: 55, top: 15 },
  slBtn: { position: 'absolute', right: 15, top: 12 },
  sectionTitle: { color: 'white', fontSize: 24, textAlign: 'center', marginBottom: 20 },
  cardBtn: { backgroundColor: 'rgba(15,23,42,0.6)', borderWidth: 1, borderColor: 'rgba(6,182,212,0.3)', borderRadius: 20, padding: 20, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 15 },
  cardRow: { flexDirection: 'row', alignItems: 'center' },
  iconBox: { width: 60, height: 60, borderRadius: 16, backgroundColor: 'rgba(255,255,255,0.1)', alignItems: 'center', justifyContent: 'center', marginRight: 15 },
  cardTextContainer: { flex: 1 },
  cardTitle: { color: 'white', fontSize: 20, fontWeight: 'bold' },
  cardDesc: { color: '#cbd5e1', fontSize: 14 }
});
