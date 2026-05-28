import React, { useState, useEffect, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, SafeAreaView, Platform, ScrollView } from 'react-native';
import { Camera, CameraType } from 'expo-camera';
import { LinearGradient } from 'expo-linear-gradient';
import { FontAwesome5 } from '@expo/vector-icons';
import { router } from 'expo-router';
import { io } from 'socket.io-client';
import { COLORS } from '../../constants/theme';

const SERVER_URL = Platform.OS === 'web' ? 'http://localhost:5000' : 'http://10.0.2.2:5000';

export default function SignLanguage() {
  const [hasPermission, setHasPermission] = useState<any>(null);
  const [currentWord, setCurrentWord] = useState('-');
  const [sentence, setSentence] = useState<string[]>([]);
  const cameraRef = useRef<any>(null);
  const socketRef = useRef<any>(null);

  useEffect(() => {
    (async () => {
      if (Platform.OS !== 'web') {
        const { status } = await Camera.requestCameraPermissionsAsync();
        setHasPermission(status === 'granted');
      } else {
        setHasPermission(true); // Assuming web handles it via navigator.mediaDevices
      }
    })();

    socketRef.current = io(SERVER_URL);
    socketRef.current.on('cv_result', (data: any) => {
       if(data.gesture) setCurrentWord(data.gesture);
    });

    const interval = setInterval(captureFrame, 1000);
    return () => {
       clearInterval(interval);
       socketRef.current?.disconnect();
    };
  }, []);

  const captureFrame = async () => {
     if (cameraRef.current) {
        try {
           const photo = await cameraRef.current.takePictureAsync({ base64: true, quality: 0.1, skipProcessing: true });
           if (photo.base64 && socketRef.current) {
              socketRef.current.emit('cv_frame', { image: photo.base64 });
           }
        } catch(e) { console.log('Camera capture error'); }
     }
  };

  const confirmWord = () => {
     if(currentWord && currentWord !== '-') {
        setSentence(prev => [...prev, currentWord]);
        setCurrentWord('-');
     }
  };

  if (hasPermission === null) return <View />;
  if (hasPermission === false) return <Text>No access to camera</Text>;

  return (
    <LinearGradient colors={['rgba(6,13,26,0.97)', '#0f172a']} style={styles.container}>
      <SafeAreaView style={{flex: 1}}>
         <View style={styles.header}>
            <View>
               <Text style={styles.brandTitle}>🤟 Sign Language Mode</Text>
               <Text style={styles.brandSubtitle}>Show hand gesture → AI reads it for you</Text>
            </View>
            <TouchableOpacity onPress={() => router.back()} style={styles.closeBtn}>
               <FontAwesome5 name="times" color="#94a3b8" size={16} />
            </TouchableOpacity>
         </View>

         <View style={styles.camContainer}>
            {Platform.OS === 'web' ? (
               <View style={styles.webCamFallback}><Text style={{color: 'white'}}>Web Camera Active (Streaming to Backend)</Text></View>
            ) : (
               <Camera style={styles.camera} type={CameraType.front} ref={cameraRef} />
            )}
            <View style={styles.liveBadge}>
               <View style={styles.liveDot} />
               <Text style={{color: COLORS.accentCyan, fontWeight: 'bold', fontSize: 10}}>AI ACTIVE</Text>
            </View>
         </View>

         <View style={styles.wordDisplayBox}>
            <Text style={{color: '#64748b', fontSize: 10, fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: 2}}>Detected Gesture</Text>
            <Text style={styles.detectedWord}>{currentWord}</Text>
            <View style={styles.progressBar}><LinearGradient colors={['#38bdf8', '#34d399']} style={{width: '60%', height: '100%'}} /></View>
            <TouchableOpacity style={styles.confirmBtn} onPress={confirmWord}>
               <Text style={{color: 'black', fontWeight: 'bold'}}>CONFIRM GESTURE</Text>
            </TouchableOpacity>
         </View>

         <ScrollView contentContainerStyle={{padding: 20}}>
            <Text style={{color: '#64748b', fontSize: 10, fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: 2, marginBottom: 10}}>Sent to AI Nurse</Text>
            <View style={styles.sentenceBox}>
               {sentence.length === 0 && <Text style={{color: '#64748b'}}>No words sent yet...</Text>}
               {sentence.map((w, i) => (
                  <View key={i} style={styles.wordBubble}><Text style={{color: 'white', fontWeight: 'bold'}}>{w}</Text></View>
               ))}
            </View>
            <TouchableOpacity style={styles.sendBtn}>
               <FontAwesome5 name="paper-plane" color="white" style={{marginRight: 10}} />
               <Text style={{color: 'white', fontWeight: 'bold', fontSize: 16}}>SEND TO TRIAGE</Text>
            </TouchableOpacity>
         </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { padding: 20, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.07)' },
  brandTitle: { color: COLORS.accentCyan, fontSize: 18, fontWeight: 'bold' },
  brandSubtitle: { color: '#64748b', fontSize: 12, marginTop: 2 },
  closeBtn: { width: 34, height: 34, borderRadius: 17, backgroundColor: 'rgba(255,255,255,0.06)', borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)', alignItems: 'center', justifyContent: 'center' },
  camContainer: { height: 250, position: 'relative', backgroundColor: '#000' },
  webCamFallback: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#0f172a' },
  camera: { flex: 1 },
  liveBadge: { position: 'absolute', top: 15, right: 15, flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(6,13,26,0.85)', borderWidth: 2, borderColor: COLORS.accentCyan, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 14, gap: 5 },
  liveDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: COLORS.riskCritical },
  wordDisplayBox: { padding: 20, borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.07)' },
  detectedWord: { color: 'white', fontSize: 40, fontWeight: '900', marginVertical: 10, textTransform: 'uppercase', letterSpacing: 2 },
  progressBar: { height: 4, backgroundColor: 'rgba(255,255,255,0.08)', borderRadius: 4, overflow: 'hidden', marginBottom: 15 },
  confirmBtn: { backgroundColor: COLORS.accentCyan, padding: 15, borderRadius: 8, alignItems: 'center' },
  sentenceBox: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 30 },
  wordBubble: { backgroundColor: 'rgba(6,182,212,0.2)', borderWidth: 1, borderColor: COLORS.accentCyan, paddingHorizontal: 15, paddingVertical: 8, borderRadius: 20 },
  sendBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: COLORS.riskCritical, padding: 20, borderRadius: 50, shadowColor: COLORS.riskCritical, shadowRadius: 10 }
});
