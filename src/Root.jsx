import {Composition} from 'remotion';
import {SampleVideo} from './SampleVideo';

export const RemotionRoot = () => {
	return (
		<Composition
			id="SampleVideo"
			component={SampleVideo}
			durationInFrames={150}
			fps={30}
			width={1920}
			height={1080}
			defaultProps={{title: 'Claude Video Editor', subtitle: 'Made with Remotion'}}
		/>
	);
};
