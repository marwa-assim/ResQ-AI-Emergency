import { Stack } from 'expo-router';

export default function RolesLayout() {
  return (
    <Stack>
      <Stack.Screen 
        name="patient" 
        options={{ 
          title: 'Patient/Volunteer SOS',
          headerStyle: { backgroundColor: '#0f172a' },
          headerTintColor: '#fff'
        }} 
      />
      <Stack.Screen 
        name="doctor" 
        options={{ 
          title: 'Doctor Portal',
          headerStyle: { backgroundColor: '#0f172a' },
          headerTintColor: '#10b981'
        }} 
      />
      <Stack.Screen 
        name="ambulance" 
        options={{ 
          title: 'Ambulance Navigator',
          headerStyle: { backgroundColor: '#0f172a' },
          headerTintColor: '#f59e0b'
        }} 
      />
    </Stack>
  );
}
