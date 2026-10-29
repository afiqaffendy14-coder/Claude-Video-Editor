import {
	AbsoluteFill,
	interpolate,
	Sequence,
	spring,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';

const Background = () => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const hue = interpolate(frame, [0, durationInFrames], [220, 300]);

	return (
		<AbsoluteFill
			style={{
				background: `linear-gradient(135deg, hsl(${hue}, 70%, 18%), hsl(${hue + 40}, 80%, 8%))`,
			}}
		/>
	);
};

const Bars = () => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();

	return (
		<AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 140}}>
			<div style={{display: 'flex', gap: 24, alignItems: 'flex-end', height: 220}}>
				{new Array(12).fill(true).map((_, i) => {
					const grow = spring({frame: frame - i * 3, fps, config: {damping: 12}});
					const wave = 0.6 + 0.4 * Math.sin((frame + i * 8) / 8);
					return (
						<div
							key={i}
							style={{
								width: 36,
								height: 220 * grow * wave,
								borderRadius: 18,
								background: `hsl(${180 + i * 12}, 90%, 65%)`,
							}}
						/>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};

const Title = ({title, subtitle}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const scale = spring({frame, fps, config: {damping: 200}});
	const subtitleOpacity = interpolate(frame, [20, 40], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});

	return (
		<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', fontFamily: 'sans-serif'}}>
			<h1
				style={{
					color: 'white',
					fontSize: 140,
					fontWeight: 800,
					margin: 0,
					transform: `scale(${scale})`,
				}}
			>
				{title}
			</h1>
			<p style={{color: '#cbd5ff', fontSize: 56, margin: 0, opacity: subtitleOpacity}}>{subtitle}</p>
		</AbsoluteFill>
	);
};

export const SampleVideo = ({title, subtitle}) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const fadeOut = interpolate(frame, [durationInFrames - 20, durationInFrames], [1, 0], {
		extrapolateLeft: 'clamp',
	});

	return (
		<AbsoluteFill style={{opacity: fadeOut}}>
			<Background />
			<Sequence from={10}>
				<Title title={title} subtitle={subtitle} />
			</Sequence>
			<Sequence from={30}>
				<Bars />
			</Sequence>
		</AbsoluteFill>
	);
};
