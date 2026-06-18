import CssBaseline from '@mui/material/CssBaseline';
import Container from '@mui/material/Container';
import Box from '@mui/material/Box';
import AppTheme from '../shared-theme/AppTheme';
import AppAppBar from './components/AppAppBar';
import AuthSection from './components/AuthSection';
import Footer from './components/Footer';

export default function Home(props: { disableCustomTheme?: boolean }) {
  return (
    <AppTheme {...props}>
      <CssBaseline enableColorScheme />
      <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
        <AppAppBar />
        <Container
          maxWidth="lg"
          component="main"
          sx={{
            display: 'flex',
            flexDirection: 'column',
            pt: { xs: 14, md: 16 },
            pb: { xs: 8, md: 10 },
            gap: { xs: 8, md: 12 },
          }}
        >
          <AuthSection />
        </Container>
        <Footer />
      </Box>
    </AppTheme>
  );
}
