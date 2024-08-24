import {StyleSheet, Image} from 'react-native';

export default function ImageViewer({ placeholderImageSource, selectedImage}) {
    const imageSource = selectedImage ? {uri: selectedImage} : placeholderImageSource;
    return (
        <Image source={placeholderImageSource} style={styles.Image} />
    )
}

const styles = StyleSheet.create({
    Image: {
        width: 320,
        height: 440,
        borderRadius: 18,
    },
})