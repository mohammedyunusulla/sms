import { Navigate } from 'react-router';
import { useAuth } from '../../../hooks/useAuth';
import StudentHomeworkPage from './StudentHomeworkPage';
import TeacherHomeworkPage from './TeacherHomeworkPage';

export default function HomeworkHub() {
  const { user } = useAuth();
  const role = (user?.role || '').toUpperCase();

  if (role === 'STUDENT' || role === 'LEARNER') {
    return <StudentHomeworkPage />;
  }
  if (role === 'TEACHER' || role === 'INSTITUTION_ADMIN' || role === 'PRINCIPAL' || role === 'SUPER_ADMIN') {
    return <TeacherHomeworkPage />;
  }
  if (role === 'PARENT' || role === 'GUARDIAN') {
    return <Navigate to="/dashboard" replace />;
  }
  return <Navigate to="/dashboard" replace />;
}
